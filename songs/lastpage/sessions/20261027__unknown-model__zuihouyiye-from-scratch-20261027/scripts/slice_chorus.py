import soundfile as sf
mix_path = "runs/production/zuihouyiye-from-scratch-20261027/render_v4/zuihouyiye_lingyuan_cover_mix_v4.wav"
data, sr = sf.read(mix_path)
sub = data[int(58.0 * sr) : int(92.0 * sr)]
sf.write("scratch/v4_chorus1_full_flow.wav", sub, sr)
print("Saved v4_chorus1_full_flow.wav")
