#!/usr/bin/env python3
"""
Demo script for Module 2: Form Inference
Shows the form inference capabilities with real examples
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def print_separator():
    print("\n" + "="*80 + "\n")

def print_form_structure(form_data):
    """Pretty print form structure"""
    print(f"📋 FORM TITLE: {form_data['title']}")
    print(f"📊 QUESTIONS: {len(form_data['questions'])}")
    print("\n" + "-"*50)
    
    for i, question in enumerate(form_data['questions'], 1):
        print(f"\nQ{i}. {question['text']}")
        print(f"    Type: {question['type']}")
        print(f"    Enabled: {question['enabled']}")
        
        if question['options']:
            print(f"    Options: {', '.join(question['options'])}")
        else:
            print(f"    Options: None (open-ended)")

def demo_inference():
    """Demonstrate form inference with various examples"""
    
    print("🎯 BERMUDA FORM INFERENCE DEMO")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator()
    
    # Check if we can import and use the inference function
    try:
        from app import infer_form_from_text
        print("✅ Successfully imported form inference function")
    except Exception as e:
        print(f"❌ Failed to import inference function: {e}")
        print("Make sure you have:")
        print("  1. OPENAI_API_KEY in your .env file")
        print("  2. Required packages installed (pip install -r requirements.txt)")
        return

    # Test examples
    examples = [
        {
            "name": "☕ Coffee Preferences Survey",
            "dump": "I want to survey coffee preferences, favorite drinks, and satisfaction ratings"
        },
        {
            "name": "🎪 Event Feedback Form",
            "dump": "Event feedback form - venue, speakers, networking, overall rating"
        },
        {
            "name": "💼 Job Application",
            "dump": "Job application: background, experience, skills, availability"
        },
        {
            "name": "🍕 Restaurant Feedback",
            "dump": "Customer satisfaction survey for our restaurant - food quality, service, atmosphere, wait time, value for money, likelihood to return"
        },
        {
            "name": "📱 Product Review",
            "dump": "We need a product review form for our new mobile app. Want to know about user interface, features, performance, bugs encountered, and overall satisfaction. Also need basic demographics."
        }
    ]
    
    successful_inferences = 0
    
    for example in examples:
        print(f"🎯 TESTING: {example['name']}")
        print(f"📝 INPUT: {example['dump']}")
        print("\n⚙️  Processing with GPT-4o-mini...")
        
        try:
            # Perform inference
            start_time = datetime.now()
            inferred_form, error = infer_form_from_text(example['dump'])
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            if inferred_form:
                print(f"✅ SUCCESS ({processing_time:.2f}s)")
                print_form_structure(inferred_form)
                successful_inferences += 1
                
                # Additional analysis
                question_types = {}
                for q in inferred_form['questions']:
                    qtype = q['type']
                    question_types[qtype] = question_types.get(qtype, 0) + 1
                
                print(f"\n📈 ANALYSIS:")
                print(f"    Question types: {dict(question_types)}")
                print(f"    Demographics included: {'age' in json.dumps(inferred_form).lower()}")
                
            else:
                print(f"❌ FAILED: {error}")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
        
        print_separator()
    
    # Summary
    print("📊 DEMO SUMMARY")
    print(f"✅ Successful inferences: {successful_inferences}/{len(examples)}")
    print(f"📈 Success rate: {(successful_inferences/len(examples))*100:.1f}%")
    
    if successful_inferences > 0:
        print("\n🎉 Form inference is working! Key features demonstrated:")
        print("  ✓ Chain-of-Thought reasoning")
        print("  ✓ Multiple question types (text, multiple_choice, rating, yes_no)")
        print("  ✓ Intelligent option generation")
        print("  ✓ Demographics integration")
        print("  ✓ JSON structure validation")
        print("  ✓ Retry logic for robustness")
    else:
        print("\n❌ No successful inferences. Please check:")
        print("  1. OPENAI_API_KEY is valid and has credits")
        print("  2. Internet connection is working")
        print("  3. All dependencies are installed")

def main():
    demo_inference()

if __name__ == "__main__":
    main()