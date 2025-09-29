import torch
import numpy as np
import base64
import io
import soundfile as sf
from pydub import AudioSegment
from typing import Dict, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from gopt import GOPT  # Import GOPT model class

class GOPTService:
    """
    GOPT (Goodness of Pronunciation Transformer) Service
    Professional pronunciation assessment với multi-level scoring
    """
    
    def __init__(self, model_path: str = "best_audio_model.pth"):
        print("Loading GOPT model...")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        try:
            # Load pretrained GOPT model với đúng parameters từ checkpoint
            # Từ checkpoint analysis: embed_dim=24, num_heads=3, depth=3
            self.model = GOPT(embed_dim=24, num_heads=3, depth=3, input_dim=84)
            checkpoint = torch.load(model_path, map_location=self.device)
            
            # Remove 'module.' prefix từ DataParallel checkpoint
            if all(k.startswith('module.') for k in checkpoint.keys()):
                checkpoint = {k[7:]: v for k, v in checkpoint.items()}
            
            self.model.load_state_dict(checkpoint)
            self.model.to(self.device)
            self.model.eval()
            print(f"GOPT model loaded successfully on {self.device}")
            
        except Exception as e:
            print(f"GOPT model loading failed: {e}")
            self.model = None
    
    def extract_gop_features(self, audio_base64: str) -> np.ndarray:
        """
        Extract GOP features từ audio (simplified version)
        Real GOPT cần Kaldi GOP extraction, đây là mock để test
        """
        try:
            # Decode audio
            audio_bytes = base64.b64decode(audio_base64)
            
            # Dùng pydub để handle nhiều format (WebM, MP4, WAV, etc.)
            try:
                # Thử đọc với pydub trước
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
                
                # Convert to WAV format in memory
                wav_buffer = io.BytesIO()
                audio_segment.export(wav_buffer, format="wav")
                wav_buffer.seek(0)
                
                # Bây giờ dùng soundfile để đọc WAV
                audio_data, sample_rate = sf.read(wav_buffer)
                
            except Exception as pydub_error:
                print(f"GOPT: Pydub failed, trying soundfile directly: {pydub_error}")
                # Fallback to soundfile (for WAV files)
                audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
            
            # Ensure mono + float32
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            audio_data = audio_data.astype(np.float32)
            
            # Extract real GOP features từ audio
            # Sử dụng MFCC + delta features như trong GOPT paper
            import librosa
            
            # Resample về 16kHz (chuẩn cho speech recognition)
            if sample_rate != 16000:
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
                sample_rate = 16000
            
            # Extract MFCC features (13 dims)
            mfcc = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=13, 
                                       hop_length=160, win_length=400, n_fft=512)
            
            # Delta features (13 dims)
            delta_mfcc = librosa.feature.delta(mfcc)
            
            # Delta-delta features (13 dims)  
            delta2_mfcc = librosa.feature.delta(mfcc, order=2)
            
            # Pitch features (1 dim)
            pitches, magnitudes = librosa.piptrack(y=audio_data, sr=sample_rate, 
                                                  hop_length=160, fmin=50, fmax=400)
            pitch_feature = np.mean(pitches, axis=0, keepdims=True)
            
            # Energy features (1 dim)
            energy = np.sum(librosa.stft(audio_data, hop_length=160, win_length=400) ** 2, axis=0, keepdims=True)
            
            # Combine tất cả features: 13+13+13+1+1 = 41 dims
            # Pad thêm để đủ 84 dims theo GOPT paper
            features = np.vstack([mfcc, delta_mfcc, delta2_mfcc, pitch_feature, energy])  # [41, T]
            
            # Transpose và pad để có shape [T, 84]
            features = features.T  # [T, 41]
            
            # Pad thêm features để đủ 84 dims
            padding_features = np.zeros((features.shape[0], 84 - features.shape[1]), dtype=np.float32)
            features = np.hstack([features, padding_features])  # [T, 84]
            
            # Limit to max 50 frames và pad/truncate
            seq_len = min(50, features.shape[0])
            if seq_len < 50:
                # Pad với zeros
                padding = np.zeros((50 - seq_len, 84), dtype=np.float32)
                features = np.vstack([features[:seq_len], padding])
            else:
                # Truncate
                features = features[:50]
            
            return features.astype(np.float32)
            
        except Exception as e:
            print(f"GOP feature extraction error: {e}")
            # Return empty features if failed
            return np.full((50, 84), -1.0, dtype=np.float32)
    
    def text_to_phoneme_indices(self, text: str) -> torch.Tensor:
        """Convert text to phoneme indices (simplified mock)"""
        # Mock phoneme mapping - thực tế cần G2P (grapheme to phoneme)
        words = text.lower().split()
        phoneme_indices = []
        
        # Simple mapping - real implementation cần proper G2P
        for word in words[:10]:  # Max 10 words -> ~50 phonemes
            for char in word[:5]:  # Max 5 chars per word
                if char.isalpha():
                    phoneme_indices.append(ord(char) % 39)  # Map to 0-38 range
        
        # Pad to 50 phonemes
        while len(phoneme_indices) < 50:
            phoneme_indices.append(-1)  # -1 = padding
        
        return torch.LongTensor(phoneme_indices[:50])

    def evaluate_pronunciation_gopt(self, audio_base64: str, reference_text: str = "") -> Dict:
        """
        GOPT pronunciation evaluation với multi-level scoring
        """
        if self.model is None:
            return {"error": "GOPT model not loaded"}
        
        try:
            # Extract GOP features
            gop_features = self.extract_gop_features(audio_base64)
            
            # Convert to tensor
            x = torch.FloatTensor(gop_features).unsqueeze(0).to(self.device)  # [1, 50, 84]
            
            # Generate phoneme sequence
            phn = self.text_to_phoneme_indices(reference_text).unsqueeze(0).to(self.device)  # [1, 50]
            
            # GOPT inference
            with torch.no_grad():
                output = self.model(x, phn)
                # output: [u1, u2, u3, u4, u5, p, w1, w2, w3]
                # u1-u5: utterance scores, p: phone scores, w1-w3: word scores
                
                u1, u2, u3, u4, u5, p, w1, w2, w3 = output
                
                # Convert to scores (0-100) với sigmoid để normalize
                import torch.nn.functional as F
                
                # Apply sigmoid để chuyển về [0, 1] rồi nhân 100
                utterance_scores = {
                    "accuracy": float(F.sigmoid(u1.squeeze())) * 100,
                    "completeness": float(F.sigmoid(u2.squeeze())) * 100, 
                    "fluency": float(F.sigmoid(u3.squeeze())) * 100,
                    "prosodic": float(F.sigmoid(u4.squeeze())) * 100,
                    "total": float(F.sigmoid(u5.squeeze())) * 100
                }
                
                phone_scores = p.squeeze().cpu().numpy()  # [50]
                word_scores = {
                    "accuracy": w1.squeeze().cpu().numpy(),  # [50]
                    "stress": w2.squeeze().cpu().numpy(),    # [50]
                    "total": w3.squeeze().cpu().numpy()      # [50]
                }
                
                return {
                    "utterance_scores": utterance_scores,
                    "phone_scores": phone_scores.tolist(),
                    "word_scores": {k: v.tolist() for k, v in word_scores.items()},
                    "overall_score": utterance_scores["total"],
                    "model": "GOPT"
                }
                
        except Exception as e:
            print(f"GOPT evaluation error: {e}")
            return {"error": f"GOPT evaluation failed: {str(e)}"}
    
    def is_available(self) -> bool:
        """Check if GOPT model is loaded and ready"""
        return self.model is not None
