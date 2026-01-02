# AsyncFirestoreSaver.py

from typing import Any, AsyncIterator, Dict, Optional, Sequence, Tuple
from contextlib import asynccontextmanager

from google.cloud.firestore import AsyncClient, Query
from google.cloud import firestore
from langchain_core.runnables import RunnableConfig

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions,
)
from langgraph.checkpoint.serde.base import (SerializerProtocol)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

class AsyncFirestoreSaver(BaseCheckpointSaver[str]):
    """
    An asynchronous LangGraph CheckpointSaver using Firestore AsyncClient.
    Optimized for high-concurrency workloads (FastAPI/Quart).
    """

    def __init__(
        self, 
        client: AsyncClient, 
        serde: Optional[SerializerProtocol] = None,
        checkpoint_collection: str = "langgraph_checkpoints",
        writes_collection: str = "langgraph_writes"
    ):
        super().__init__(serde=serde or JsonPlusSerializer())
        self.client = client
        self.checkpoint_collection = self.client.collection(checkpoint_collection)
        self.writes_collection = self.client.collection(writes_collection)

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Asynchronously save a checkpoint."""
        configuration = config.get("configurable", {})
        
        thread_id = configuration.get("thread_id")
        checkpoint_ns = configuration.get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = configuration.get("checkpoint_id")
        
        if not thread_id:
            raise ValueError("Missing 'thread_id' in config['configurable']")

        # Serialize
        type_, checkpoint_bytes = self.serde.dumps_typed(checkpoint)
        meta_type_, meta_bytes = self.serde.dumps_typed(metadata)

        doc_data = {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint_id,
            "parent_checkpoint_id": parent_checkpoint_id,
            "checkpoint": checkpoint_bytes,
            "checkpoint_type": type_,
            "metadata": meta_bytes,
            "metadata_type": meta_type_,
            "created_at": firestore.SERVER_TIMESTAMP 
        }

        # Upsert asynchronously
        doc_ref = self.checkpoint_collection.document(f"{thread_id}_{checkpoint_id}")
        await doc_ref.set(doc_data)

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Asynchronously store intermediate writes."""
        configuration = config.get("configurable", {})
        
        thread_id = configuration.get("thread_id")
        checkpoint_ns = configuration.get("checkpoint_ns", "")
        checkpoint_id = configuration.get("checkpoint_id")

        # Use an async batch for atomicity and performance
        batch = self.client.batch()
        
        for idx, (channel, value) in enumerate(writes):
            type_, value_bytes = self.serde.dumps_typed(value)
            
            write_data = {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "task_path": task_path,
                "channel": channel,
                "type": type_,
                "value": value_bytes,
                "idx": idx,
                "created_at": firestore.SERVER_TIMESTAMP
            }
            
            doc_id = f"{thread_id}_{checkpoint_id}_{task_id}_{idx}"
            doc_ref = self.writes_collection.document(doc_id)
            batch.set(doc_ref, write_data)
            
        await batch.commit()

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Asynchronously retrieve a checkpoint tuple."""
        configuration = config.get("configurable", {})
        thread_id = configuration.get("thread_id")
        checkpoint_ns = configuration.get("checkpoint_ns", "")
        checkpoint_id = configuration.get("checkpoint_id")

        data = None
        # data: Optional[Dict[str, Any]] = None
        if checkpoint_id:
            # Direct lookup
            doc_ref = self.checkpoint_collection.document(f"{thread_id}_{checkpoint_id}")
            snapshot = await doc_ref.get()
            if snapshot.exists:
                data = snapshot.to_dict()
        else:
            # Query for latest
            query = (
                self.checkpoint_collection
                .where(filter=firestore.FieldFilter("thread_id", "==", thread_id))
                .where(filter=firestore.FieldFilter("checkpoint_ns", "==", checkpoint_ns))
                .order_by("checkpoint_id", direction=firestore.Query.DESCENDING)
                .limit(1)
            )
            # stream() returns an async iterator
            async for doc in query.stream():
                data = doc.to_dict()
                break

        if not data:
            return None
        
        # if data is None:
            # return None

        # Deserialize
        checkpoint = self.serde.loads_typed((data["checkpoint_type"], data["checkpoint"]))
        metadata = self.serde.loads_typed((data["metadata_type"], data["metadata"]))
        
        # Fetch pending writes asynchronously
        final_checkpoint_id = data["checkpoint_id"]
        parent_checkpoint_id = data.get("parent_checkpoint_id")

        pending_writes = []
        writes_query = (
            self.writes_collection
            .where(filter=firestore.FieldFilter("thread_id", "==", thread_id))
            .where(filter=firestore.FieldFilter("checkpoint_id", "==", final_checkpoint_id))
            .order_by("task_id")
            .order_by("idx")
        )

        async for w_doc in writes_query.stream():
            w_data = w_doc.to_dict()
            if w_data is None:
                continue
            val = self.serde.loads_typed((w_data["type"], w_data["value"]))
            pending_writes.append((w_data["task_id"], w_data["channel"], val))

        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": parent_checkpoint_id,
                }
            } if parent_checkpoint_id else None,
            pending_writes=pending_writes,
        )

    async def alist(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """Asynchronously list checkpoints."""
        
        configuration = config.get("configurable", {}) if config else {}
        thread_id = configuration.get("thread_id")
        checkpoint_ns = configuration.get("checkpoint_ns", "")
        
        query = (
            self.checkpoint_collection
            .where(filter=firestore.FieldFilter("thread_id", "==", thread_id))
            .where(filter=firestore.FieldFilter("checkpoint_ns", "==", checkpoint_ns))
            .order_by("checkpoint_id", direction=firestore.Query.DESCENDING)
        )

        if before:
            # Use .get("configurable", {}) instead of ["configurable"]
            # This handles both 'before' being Optional and 'configurable' being optional
            before_config = before.get("configurable", {})
            before_id = before_config.get("checkpoint_id")
            if before_id:
                query = query.start_after({"checkpoint_id": before_id})

        if limit:
            query = query.limit(limit)

        async for doc in query.stream():
            data = doc.to_dict()
            if not data:
                return
            checkpoint = self.serde.loads_typed((data["checkpoint_type"], data["checkpoint"]))
            metadata = self.serde.loads_typed((data["metadata_type"], data["metadata"]))
            
            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": data["thread_id"],
                        "checkpoint_ns": data["checkpoint_ns"],
                        "checkpoint_id": data["checkpoint_id"],
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config={
                    "configurable": {
                        "thread_id": data["thread_id"],
                        "checkpoint_ns": data["checkpoint_ns"],
                        "checkpoint_id": data.get("parent_checkpoint_id"),
                    }
                } if data.get("parent_checkpoint_id") else None,
            )

    # Note: We purposely do NOT implement the synchronous methods (get, put, list).
    # Using a sync method with an AsyncClient will crash or require messy event loops.
    # If the user tries to use this in a sync graph.invoke(), it should raise standard NotImplementedError.
