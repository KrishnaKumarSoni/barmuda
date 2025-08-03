"""
Test data fixtures and factories for consistent test data generation
"""

import factory
from faker import Faker
from datetime import datetime

fake = Faker()


class FormFactory(factory.DictFactory):
    """Factory for generating test form data"""

    id = factory.LazyFunction(lambda: f"form_{fake.random_int(100, 999)}")
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=4)[:-1])
    description = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    creator_id = "test_user_123"
    active = False
    created_at = factory.LazyFunction(lambda: datetime.now().isoformat())

    @factory.lazy_attribute
    def questions(self):
        return [
            {
                "text": "How satisfied are you with our service?",
                "type": "rating",
                "enabled": True,
                "options": ["1", "2", "3", "4", "5"],
            },
            {"text": "What could we improve?", "type": "text", "enabled": True},
        ]

    @factory.lazy_attribute
    def demographics(self):
        return {
            "enabled": True,
            "age": {"enabled": True},
            "gender": {"enabled": True},
            "location": {"enabled": False},
        }


class ChatSessionFactory(factory.DictFactory):
    """Factory for generating test chat session data"""

    session_id = factory.LazyFunction(lambda: f"session_{fake.uuid4()[:8]}")
    form_id = "test_form_123"
    device_id = factory.LazyFunction(lambda: f"device_{fake.uuid4()[:8]}")
    status = "active"
    message_count = 3
    started_at = factory.LazyFunction(lambda: datetime.now().isoformat())

    @factory.lazy_attribute
    def location(self):
        return {"country": fake.country_code(), "city": fake.city()}

    @factory.lazy_attribute
    def responses(self):
        return {
            "0": {"answer": "4", "question": "How satisfied are you with our service?"},
            "1": {
                "answer": "More features please",
                "question": "What could we improve?",
            },
        }


class ResponseFactory(factory.DictFactory):
    """Factory for generating test response data"""

    session_id = factory.LazyFunction(lambda: f"session_{fake.uuid4()[:8]}")
    device_id = factory.LazyFunction(lambda: f"device_{fake.uuid4()[:8]}")

    @factory.lazy_attribute
    def responses(self):
        return {"0": str(fake.random_int(1, 5)), "1": fake.sentence()}

    @factory.lazy_attribute
    def metadata(self):
        return {
            "partial": False,
            "completed_at": datetime.now().isoformat(),
            "device_id": self.device_id,
        }

    @factory.lazy_attribute
    def demographics(self):
        return {
            "age": fake.random_element(["18-24", "25-30", "31-40", "41-50", "50+"]),
            "gender": fake.random_element(
                ["Male", "Female", "Other", "Prefer not to say"]
            ),
        }


# Common test data
SAMPLE_TEMPLATES = {
    "customer_feedback": {
        "title": "Customer Feedback Survey",
        "description": "Help us improve our service",
        "questions": [
            {"text": "How satisfied are you?", "type": "rating", "enabled": True},
            {"text": "What can we improve?", "type": "text", "enabled": True},
        ],
    },
    "employee_survey": {
        "title": "Employee Satisfaction Survey",
        "description": "Anonymous employee feedback",
        "questions": [
            {"text": "How happy are you at work?", "type": "rating", "enabled": True},
            {
                "text": "What would improve your experience?",
                "type": "text",
                "enabled": True,
            },
        ],
    },
}

EDGE_CASE_MESSAGES = {
    "off_topic": [
        "What's the weather like?",
        "Tell me about bananas",
        "I like cats",
        "How do I cook pasta?",
    ],
    "skip_requests": [
        "Skip this question",
        "I don't want to answer",
        "Pass",
        "Next question please",
        "I'd rather not say",
    ],
    "multi_answers": [
        "Alex, 25, from LA",
        "I'm 30 and work as an engineer in New York",
        "Sarah, age 27, female, from Chicago",
    ],
    "conflicting": [
        ("Yes, I love it", "Actually, no I don't"),
        ("I'm very satisfied", "Wait, I'm not satisfied"),
        ("5 out of 5", "Actually more like a 2"),
    ],
    "vague": ["meh", "kinda", "not really sure", "maybe", "sometimes"],
}

INVALID_INPUTS = [
    # SQL injection attempts
    "'; DROP TABLE forms; --",
    "1' OR '1'='1",
    # XSS attempts
    "<script>alert('xss')</script>",
    "javascript:alert('xss')",
    # Large inputs
    "x" * 10000,
    # Special characters
    "Test with 'quotes' and \"double quotes\"",
    "Test with unicode: 你好 🎉 ñoño",
    # Empty/null inputs
    "",
    None,
    "   ",  # Whitespace only
]
