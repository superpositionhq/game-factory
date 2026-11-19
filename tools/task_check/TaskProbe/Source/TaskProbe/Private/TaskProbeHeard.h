// What a play's player hears (the `heard` query, game grader 1.26.0): the game's own mixed output, read from the
// engine's main submix as it renders, before -muteaudio silences the device. Every 50 ms block of the mix becomes one
// sample: its loudness and peak (dBFS) and its energy in eight octave bands (63 Hz to 8 kHz, dB). A play may also ask for
// clips of the mix, written as 16-bit mono WAV files next to probe.json for an audio judge to listen to.
// docs/planning/2026-11-19_game-grader-heard/spec.md

#pragma once

#include "CoreMinimal.h"
#include "ISubmixBufferListener.h"
#include <atomic>

class FJsonObject;
class FJsonValue;
class FAudioDevice;

namespace TaskProbe
{
	class FMix : public ISubmixBufferListener
	{
	public:
		static constexpr int32 Bands = 8;
		static constexpr double BlockSeconds = 0.05;  // one sample of the mix
		static constexpr int32 ClipRate = 16000;  // a clip's samples per second (at most; the mix's rate over a whole number)
		static constexpr double ClipSeconds = 30.0;  // one clip at most
		static constexpr double ClipsSeconds = 120.0;  // every clip of a play together at most
		static constexpr int32 MaxClips = 8;
		static constexpr int32 MaxBlocks = 40000;  // a 1200 s play is 24,000 blocks

		/** The clips the query asks for ({"clips": [{"name", "from", "to"}]}, play seconds); problems go to Errors. */
		void Configure(const TSharedPtr<FJsonObject>& Def, TArray<FString>& Errors);
		/** Every frame of the play, on the game thread: the play's clock as its blocks are stamped, and the listener
		 *  registered with the main submix once a device is there. */
		void Tick(FAudioDevice* Device, double T);
		/** Taken off the submix (the probe ends). */
		void Stop();
		/** The blocks as samples, [{t, value: {loudness, peak, "band:63", ...}}], for probe.json's measures. */
		TArray<TSharedPtr<FJsonValue>> SamplesJson();
		/** Every clip with samples written to Dir as heard_<name>.wav: the files' names. */
		TArray<FString> WriteClips(const FString& Dir);

		// ISubmixBufferListener (the audio render thread)
		virtual void OnNewSubmixBuffer(const USoundSubmix* OwningSubmix, float* AudioData, int32 NumSamples, int32 NumChannels,
			const int32 SampleRate, double AudioClock) override;
		virtual bool IsRenderingAudio() const override { return true; }  // a silent mix is still read (its loudness)
		virtual const FString& GetListenerName() const override;

	private:
		struct FBiquad
		{
			double B0 = 0.0, B1 = 0.0, B2 = 0.0, A1 = 0.0, A2 = 0.0;
			double X1 = 0.0, X2 = 0.0, Y1 = 0.0, Y2 = 0.0;
			bool bOn = false;
		};
		struct FBlock
		{
			double T = 0.0;
			float Loudness = 0.f, Peak = 0.f;
			float Band[Bands] = {};
		};
		struct FClip
		{
			FString Name;
			double From = 0.0, To = 0.0;
			TArray<int16> Samples;
		};
		void Setup(int32 SampleRate);

		FCriticalSection Lock;
		std::atomic<double> PlayT{-1.0};  // the play's clock, as the game thread last set it (-1: not started)
		int32 Rate = 0;
		int32 BlockFrames = 0;
		int32 InBlock = 0;
		double SumSq = 0.0, Peak = 0.0;
		double BandSq[Bands] = {};
		FBiquad Filters[Bands];
		int32 Decimate = 1, InDecimate = 0;
		double DecimateSum = 0.0;
		TArray<FBlock> Blocks;
		bool bCapped = false;
		TArray<FClip> Clips;
		bool bRegistered = false;
		uint32 DeviceId = 0;
	};
}
