import base64
import io
import numpy as np
import parselmouth
import soundfile as sf


class ProsodyService:
    """
    Service phân tích prosody (intonation & stress) từ audio.
    - Trích xuất pitch contour
    - Tính điểm intonation dựa trên sự thay đổi pitch
    """

    def __init__(self):
        self.min_pitch = 75  # Hz
        self.max_pitch = 500  # Hz

    def analyze_prosody_base64(self, audio_base64: str) -> dict:
        try:
            # Decode base64 to audio bytes
            audio_bytes = base64.b64decode(audio_base64)
            audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
            # Nếu stereo, chuyển mono
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            # Chuyển sang float32
            audio_data = audio_data.astype(np.float32)
            # Tạo Sound object cho parselmouth
            snd = parselmouth.Sound(audio_data, sample_rate)
            # Trích xuất pitch contour
            pitch = snd.to_pitch(
                time_step=0.01, pitch_floor=self.min_pitch, pitch_ceiling=self.max_pitch
            )
            pitch_values = pitch.selected_array["frequency"]
            # Lọc các giá trị pitch hợp lệ
            valid_pitches = pitch_values[
                (pitch_values > 0) & (pitch_values < self.max_pitch)
            ]
            if len(valid_pitches) < 5:
                return {
                    "intonation_score": 0.0,
                    "stress_score": 0.0,
                    "pitch_range": 0.0,
                    "pitch_std": 0.0,
                    "message": "Không đủ dữ liệu pitch để đánh giá.",
                }
            # Tính range và std
            pitch_range = np.max(valid_pitches) - np.min(valid_pitches)
            pitch_std = np.std(valid_pitches)
            # Công thức điểm intonation: càng nhiều biến thiên pitch càng tốt (nhưng không quá lớn)
            range_score = min(1.0, max(0.0, (pitch_range - 40) / 160))
            std_score = min(1.0, max(0.0, (pitch_std - 20) / 60))
            intonation_score = (range_score * 0.6 + std_score * 0.4) * 100
            # Tính stress: dựa vào độ chênh lệch pitch giữa các vùng (peak-to-valley)
            # Đơn giản: tính số lần pitch tăng mạnh rồi giảm mạnh (local maxima)
            from scipy.signal import find_peaks

            peaks, _ = find_peaks(valid_pitches, prominence=10)
            valleys, _ = find_peaks(-valid_pitches, prominence=10)
            n_peaks = len(peaks)
            n_valleys = len(valleys)
            # Nếu có nhiều peak/valley rõ rệt, coi là stress tốt (giả lập nhấn âm)
            stress_score = (
                min(1.0, (n_peaks + n_valleys) / 8) * 100
            )  # 8 là số peak lý tưởng cho 1 câu dài
            return {
                "intonation_score": round(intonation_score, 1),
                "stress_score": round(stress_score, 1),
                "pitch_range": round(pitch_range, 1),
                "pitch_std": round(pitch_std, 1),
                "message": "Đánh giá intonation & stress thành công.",
            }
        except Exception as e:
            return {
                "intonation_score": 0.0,
                "stress_score": 0.0,
                "pitch_range": 0.0,
                "pitch_std": 0.0,
                "message": f"Lỗi prosody: {e}",
            }
