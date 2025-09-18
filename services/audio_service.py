import base64
import io
import numpy as np
import soundfile as sf
from typing import Tuple
from models import AudioAnalysis

class AudioService:
    """
    Audio quality analysis and validation service
    
    Features:
    - Audio format validation
    - Quality assessment (SNR, duration, etc.)
    - Audio preprocessing for optimal transcription
    """
    
    def __init__(self):
        self.min_duration = 0.5 
        self.max_duration = 30.0 
        self.target_sample_rate = 16000  
    
    def analyze_audio_base64(self, audio_base64: str) -> AudioAnalysis:
        try:
            # Decode base64 to audio bytes
            audio_bytes = base64.b64decode(audio_base64)
            
            # Load audio data
            audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
            
            # Ensure mono audio
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
                channels = audio_data.shape[1] if len(audio_data.shape) > 1 else 1
            else:
                channels = 1
            
            # Calculate duration
            duration = len(audio_data) / sample_rate
            
            # Analyze audio quality
            quality_score, issues = self._analyze_quality(audio_data, duration, sample_rate)
            
            # More lenient validation for learner audio
            critical_issues = [issue for issue in issues if "warning" not in issue.lower() and "very long" not in issue.lower()]
            is_valid = len(critical_issues) == 0
            
            return AudioAnalysis(
                is_valid=is_valid,
                duration=round(duration, 2),
                sample_rate=sample_rate,
                channels=channels,
                issues=issues,
                quality_score=round(quality_score, 2)
            )
            
        except Exception as e:
            return AudioAnalysis(
                is_valid=False,
                duration=0.0,
                sample_rate=0,
                channels=0,
                issues=[f"Audio processing error: {str(e)}"],
                quality_score=0.0
            )
    
    def _analyze_quality(self, audio_data: np.ndarray, duration: float, sample_rate: int) -> Tuple[float, list]:
        """
        Analyze audio quality and detect issues
        
        Returns:
            Tuple of (quality_score, issues_list)
        """
        issues = []
        quality_factors = []
        
        # Check duration
        if duration < self.min_duration:
            issues.append(f"Audio too short ({duration:.1f}s). Minimum {self.min_duration}s required.")
            quality_factors.append(0.2)
        elif duration > self.max_duration:
            issues.append(f"Warning: Audio very long ({duration:.1f}s). Consider shorter recordings.")
            quality_factors.append(0.8)
        else:
            quality_factors.append(1.0)
        
        # Check sample rate
        if sample_rate < 8000:
            issues.append(f"Low sample rate ({sample_rate}Hz). Recommend 16kHz or higher.")
            quality_factors.append(0.3)
        elif sample_rate < 16000:
            issues.append(f"Warning: Sample rate could be higher ({sample_rate}Hz vs 16kHz ideal).")
            quality_factors.append(0.7)
        else:
            quality_factors.append(1.0)
        
        # Check for silence/low volume
        rms_level = np.sqrt(np.mean(audio_data**2))
        if rms_level < 0.01:
            issues.append("Audio level very low. Speak closer to microphone.")
            quality_factors.append(0.2)
        elif rms_level < 0.05:
            issues.append("Warning: Audio level low. Consider speaking louder.")
            quality_factors.append(0.6)
        else:
            quality_factors.append(1.0)
        
        # Check for clipping
        clipping_ratio = np.sum(np.abs(audio_data) > 0.95) / len(audio_data)
        if clipping_ratio > 0.01:
            issues.append("Audio clipping detected. Reduce microphone gain.")
            quality_factors.append(0.3)
        elif clipping_ratio > 0.001:
            issues.append("Warning: Minor audio clipping detected.")
            quality_factors.append(0.7)
        else:
            quality_factors.append(1.0)
        
        # Estimate SNR (Signal-to-Noise Ratio)
        snr_score = self._estimate_snr(audio_data)
        if snr_score < 10:
            issues.append("High background noise detected. Find a quieter environment.")
            quality_factors.append(0.3)
        elif snr_score < 20:
            issues.append("Warning: Background noise present.")
            quality_factors.append(0.7)
        else:
            quality_factors.append(1.0)
        
        # Calculate overall quality score
        quality_score = np.mean(quality_factors) * 100
        
        return quality_score, issues
    
    def _estimate_snr(self, audio: np.ndarray) -> float:
        """
        Estimate Signal-to-Noise Ratio
        
        Simple estimation based on energy distribution
        """
        try:
            # Calculate frame energies
            frame_size = 1024
            hop_size = 512
            
            energies = []
            for i in range(0, len(audio) - frame_size, hop_size):
                frame = audio[i:i + frame_size]
                energy = np.sum(frame**2)
                energies.append(energy)
            
            if not energies:
                return 20.0  # Default reasonable SNR
            
            energies = np.array(energies)
            
            # Estimate noise floor (10th percentile)
            noise_energy = np.percentile(energies, 10)
            
            # Estimate signal energy (90th percentile)
            signal_energy = np.percentile(energies, 90)
            
            if noise_energy <= 0:
                return 30.0  # Very clean signal
            
            # SNR in dB
            snr_db = 10 * np.log10(signal_energy / noise_energy)
            
            return max(0, min(40, snr_db))  # Clamp between 0-40 dB
            
        except:
            return 20.0  # Default fallback
    
    def get_supported_formats(self) -> list:
        """Return list of supported audio formats"""
        return ["wav", "mp3", "m4a", "flac", "ogg"]
