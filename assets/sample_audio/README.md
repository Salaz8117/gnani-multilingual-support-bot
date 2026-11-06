# Sample Audio Directory

The four scenario buttons use small synthetic tone WAVs so the demo works out
of the box. The mock clients return simulated transcripts; the files are not
recordings of speech. To regenerate them, run `python scripts/generate_audio_samples.py`.

Replace these samples with real recordings if desired:

- hinglish_refund_noisy.wav - Hinglish refund request with background noise
- tamil_complaint.wav - Tamil product complaint
- english_order_status.wav - English order status query
- bengali_technical.wav - Bengali technical support request

Format: WAV, 16kHz, mono preferred
Max size: 25MB per file

Keep WAVs at 16 kHz, mono, and under 1 MB for each committed sample.