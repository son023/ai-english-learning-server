# AI English Learning Server - Comprehensive Test Client

import requests
import base64
import json
from pathlib import Path

# FastAPI server URL
url = "http://localhost:8000/evaluate-pronunciation"

def test_pronunciation(audio_file_path, reference_sentence, test_name="Test"):
    """Test pronunciation with specific audio file"""
    print(f"\n {test_name}")
    print("=" * 60)
    print(f" Audio file: {audio_file_path}")
    print(f" Reference: '{reference_sentence}'")
    
    # Check if file exists
    if not Path(audio_file_path).exists():
        print(f" Audio file not found: {audio_file_path}")
        return False
    
    try:
        # Convert audio to base64 (FastAPI format)
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Prepare JSON request data for FastAPI
        request_data = {
            "audio_base64": audio_base64,
            "sentence": reference_sentence
        }
        
        print(f" Sending request to {url}...")
        
        # Send POST request with JSON
        response = requests.post(
            url, 
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # Process response
        if response.status_code == 200:
            result = response.json()
            print(" SUCCESS! Detailed Analysis:")
            print("-" * 50)
            
            # Basic comparison
            print(f" Reference:     '{result['original_sentence']}'")
            print(f"  Transcribed:   '{result['transcribed_text']}'")
            print(f" Confidence:    {result['confidence']:.2f}")
            print(f" WER Score:     {result['wer_score']:.3f}")
            
            # Pronunciation scores
            scores = result['scores']
            print(f"\n SCORES:")
            print(f"    Overall:       {scores['overall']:.1f}/100")
            print(f"    Pronunciation: {scores['pronunciation']:.1f}/100")
            print(f"    Fluency:       {scores['fluency']:.1f}/100")
            print(f"    Intonation:    {scores['intonation']:.1f}/100")
            print(f"    Stress:        {scores['stress']:.1f}/100")
            
            # Performance assessment
            overall_score = scores['overall']
            if overall_score >= 90:
                performance = " EXCELLENT"
            elif overall_score >= 75:
                performance = " GOOD"
            elif overall_score >= 60:
                performance = " FAIR"
            else:
                performance = " NEEDS IMPROVEMENT"
            print(f"     Assessment:    {performance}")
            
            # Word-level errors
            word_errors = result['word_errors']
            if word_errors:
                print(f"\n  WORD ERRORS ({len(word_errors)} found):")
                for i, error in enumerate(word_errors, 1):
                    severity_icons = {"low": "🟡", "moderate": "🟠", "high": "🔴"}
                    icon = severity_icons.get(error['severity'], "⚪")
                    print(f"   {i}. {icon} Position {error['position']}: '{error['expected']}' → '{error['actual']}'")
                    print(f"       Type: {error['error_type']}")
                    print(f"       Severity: {error['severity']}")
            else:
                print("\n✅ PERFECT! No word errors detected!")
            
            # Phonetic analysis
            if result.get('reference_phonetics') and result.get('transcribed_phonetics'):
                print(f"\n PHONETIC ANALYSIS:")
                print(f"    Reference:  {result['reference_phonetics']}")
                print(f"    Transcribed: {result['transcribed_phonetics']}")
            
            # AI Feedback
            print(f"\n AI FEEDBACK:")
            feedback_lines = result['feedback'].split('. ')
            for line in feedback_lines:
                if line.strip():
                    print(f"   • {line.strip()}")
            
            print("-" * 50)
            return True
            
        else:
            print(f" Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f" Request failed: {e}")
        return False

def main():
    """Main testing function"""
    print(" AI ENGLISH LEARNING SERVER - COMPREHENSIVE AUDIO TEST")
    print("=" * 70)
    
    # Test cases: audio_file, reference_text, test_name
    test_cases = [
        # Teacher pronunciations (should be perfect)
        ("audios/teacher/today.wav", "Today is the 13th of May 2023", "TEACHER: 'Today is the 13th of May 2023'"),
        ("audios/teacher/interesting.wav", "Interesting", "TEACHER: 'Interesting'"),
        ("audios/teacher/youtube.wav", "I would like to watch YouTube", "TEACHER: 'I would like to watch YouTube'"),
        ("audios/teacher/euros.wav", "I have 2.5 euros", "TEACHER: 'I have 2.5 euros'"),
        ("audios/teacher/won.wav", "One", "TEACHER: 'One'"),
        
        # Learner pronunciations (may have errors)
        ("audios/learner/today.wav", "Today is the 13th of May 2023", "LEARNER: 'Today is the 13th of May 2023'"),
        ("audios/learner/interesting.wav", "Interesting", "LEARNER: 'Interesting'"),
        ("audios/learner/youtube.wav", "I would like to watch YouTube", "LEARNER: 'I would like to watch YouTube'"),
        ("audios/learner/euros.wav", "I have 2.5 euros", "LEARNER: 'I have 2.5 euros'"),
        ("audios/learner/won.wav", "One", "LEARNER: 'One'"),
        
    ]
    
    successful_tests = 0
    total_tests = 0
    
    for audio_file, reference, test_name in test_cases:
        if Path(audio_file).exists():
            total_tests += 1
            success = test_pronunciation(audio_file, reference, test_name)
            if success:
                successful_tests += 1
        else:
            print(f"\n  File not found, skipping: {audio_file}")
    
    # Summary
    print(f"\n TESTING SUMMARY")
    print("=" * 70)
    print(f" Successful tests: {successful_tests}/{total_tests}")
    if total_tests > 0:
        success_rate = (successful_tests / total_tests) * 100
        print(f" Success rate: {success_rate:.1f}%")
        
        if successful_tests == total_tests:
            print(" ALL TESTS PASSED! Pronunciation evaluation system working perfectly!")
        elif successful_tests > 0:
            print("  Some tests passed. Check failed tests for issues.")
        else:
            print(" All tests failed. Check server and audio files.")
    else:
        print(" No audio files found to test.")

if __name__ == "__main__":
    main()