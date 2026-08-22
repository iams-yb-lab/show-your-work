from kokoro import KPipeline
import torch, soundfile as sf, numpy as np

pipe = KPipeline(lang_code="a", device="cuda")
text = ("In the beginning, there was only silence. Then, from the silence, an instrument was born. "
        "Patient, precise, and calm beyond measure, it waited for its purpose.")
chunks = [a for _, _, a in pipe(text, voice="am_onyx", speed=0.88)]
y = torch.cat(chunks).numpy().astype(np.float32)
out = r"C:\Users\iams1\AppData\Local\Temp\temperature-controller-media\onyx_prompt.wav"
sf.write(out, y, 24000)
print("prompt dur", len(y) / 24000)
