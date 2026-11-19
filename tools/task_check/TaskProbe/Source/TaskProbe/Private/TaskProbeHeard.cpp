#include "TaskProbeHeard.h"

#include "AudioDevice.h"
#include "AudioDeviceManager.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Engine.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Sound/SoundSubmix.h"

namespace TaskProbe
{
	// the octave bands' centres (Hz); a band at or above 0.45 of the mix's rate reads as silence
	static const double BandCentres[FMix::Bands] = {63.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0};
	static const TCHAR* BandNames[FMix::Bands] = {TEXT("band:63"), TEXT("band:125"), TEXT("band:250"), TEXT("band:500"),
		TEXT("band:1000"), TEXT("band:2000"), TEXT("band:4000"), TEXT("band:8000")};
	static constexpr double Floor = -100.0;  // the dB a silent block reads

	static double Db(double Power)
	{
		return Power > 1e-10 ? FMath::Max(Floor, 10.0 * FMath::LogX(10.0, Power)) : Floor;
	}

	void FMix::Configure(const TSharedPtr<FJsonObject>& Def, TArray<FString>& Errors)
	{
		const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
		if (!Def.IsValid() || !Def->TryGetArrayField(TEXT("clips"), List))
		{
			return;
		}
		double Total = 0.0;
		for (const TSharedPtr<FJsonValue>& Item : *List)
		{
			const TSharedPtr<FJsonObject>* Obj = nullptr;
			FClip C;
			if (!Item.IsValid() || !Item->TryGetObject(Obj) || !(*Obj)->TryGetStringField(TEXT("name"), C.Name)
				|| !(*Obj)->TryGetNumberField(TEXT("from"), C.From) || !(*Obj)->TryGetNumberField(TEXT("to"), C.To))
			{
				Errors.Add(TEXT("heard: a clip is not {name, from, to}"));
				continue;
			}
			bool bPlain = !C.Name.IsEmpty() && C.Name.Len() <= 32;
			for (const TCHAR Ch : C.Name)
			{
				bPlain = bPlain && ((Ch >= 'a' && Ch <= 'z') || (Ch >= '0' && Ch <= '9') || Ch == '_');
			}
			const double Long = C.To - C.From;
			if (!bPlain || C.From < 0.0 || Long <= 0.0 || Long > ClipSeconds + 1e-6 || Clips.Num() >= MaxClips
				|| Total + Long > ClipsSeconds + 1e-6 || Clips.ContainsByPredicate([&C](const FClip& O) { return O.Name == C.Name; }))
			{
				Errors.Add(FString::Printf(TEXT("heard: clip '%s' left out (a name of a-z, 0-9 and _, at most %d clips of %g s, %g s in all)"),
					*C.Name, MaxClips, ClipSeconds, ClipsSeconds));
				continue;
			}
			Total += Long;
			Clips.Add(MoveTemp(C));
		}
	}

	const FString& FMix::GetListenerName() const
	{
		static const FString Name(TEXT("TaskProbeHeard"));
		return Name;
	}

	void FMix::Tick(FAudioDevice* Device, double T)
	{
		PlayT.store(T);
		if (!bRegistered && Device)
		{
			Device->RegisterSubmixBufferListener(AsShared(), Device->GetMainSubmixObject());
			DeviceId = Device->DeviceID;
			bRegistered = true;
		}
	}

	void FMix::Stop()
	{
		PlayT.store(-1.0);
		if (!bRegistered || !GEngine)
		{
			return;
		}
		bRegistered = false;
		if (FAudioDeviceManager* Manager = GEngine->GetAudioDeviceManager())
		{
			if (FAudioDevice* Device = Manager->GetAudioDeviceRaw(DeviceId))
			{
				Device->UnregisterSubmixBufferListener(AsShared(), Device->GetMainSubmixObject());
			}
		}
	}

	void FMix::Setup(int32 SampleRate)
	{
		Rate = SampleRate;
		BlockFrames = FMath::Max(1, FMath::RoundToInt(SampleRate * BlockSeconds));
		InBlock = 0;
		SumSq = Peak = 0.0;
		Decimate = FMath::Max(1, FMath::DivideAndRoundUp(SampleRate, ClipRate));
		InDecimate = 0;
		DecimateSum = 0.0;
		for (int32 B = 0; B < Bands; ++B)
		{
			// RBJ band-pass, 0 dB at its centre, an octave wide (Q = sqrt 2)
			FBiquad& F = Filters[B];
			F = FBiquad();
			BandSq[B] = 0.0;
			if (BandCentres[B] >= 0.45 * SampleRate)
			{
				continue;
			}
			const double W0 = 2.0 * UE_DOUBLE_PI * BandCentres[B] / SampleRate;
			const double Alpha = FMath::Sin(W0) / (2.0 * UE_DOUBLE_SQRT_2);
			const double A0 = 1.0 + Alpha;
			F.B0 = Alpha / A0;
			F.B1 = 0.0;
			F.B2 = -Alpha / A0;
			F.A1 = -2.0 * FMath::Cos(W0) / A0;
			F.A2 = (1.0 - Alpha) / A0;
			F.bOn = true;
		}
	}

	void FMix::OnNewSubmixBuffer(const USoundSubmix* OwningSubmix, float* AudioData, int32 NumSamples, int32 NumChannels,
		const int32 SampleRate, double AudioClock)
	{
		const double T = PlayT.load();
		if (T < 0.0 || !AudioData || NumChannels <= 0 || SampleRate <= 0)
		{
			return;
		}
		FScopeLock Locked(&Lock);
		if (Rate != SampleRate)
		{
			Setup(SampleRate);
		}
		const int32 Frames = NumSamples / NumChannels;
		const double ClipScale = 1.0 / Decimate;
		for (int32 Fr = 0; Fr < Frames; ++Fr)
		{
			// the mix as one channel: the mean of its channels
			double X = 0.0;
			for (int32 Ch = 0; Ch < NumChannels; ++Ch)
			{
				X += AudioData[Fr * NumChannels + Ch];
			}
			X /= NumChannels;
			SumSq += X * X;
			Peak = FMath::Max(Peak, FMath::Abs(X));
			for (int32 B = 0; B < Bands; ++B)
			{
				FBiquad& F = Filters[B];
				if (!F.bOn)
				{
					continue;
				}
				const double Y = F.B0 * X + F.B1 * F.X1 + F.B2 * F.X2 - F.A1 * F.Y1 - F.A2 * F.Y2;
				F.X2 = F.X1;
				F.X1 = X;
				F.Y2 = F.Y1;
				F.Y1 = FMath::IsFinite(Y) ? Y : 0.0;
				BandSq[B] += F.Y1 * F.Y1;
			}
			DecimateSum += X;
			if (++InDecimate >= Decimate)
			{
				const int16 Out = (int16)FMath::Clamp(FMath::RoundToInt(DecimateSum * ClipScale * 32767.0), -32768, 32767);
				for (FClip& C : Clips)
				{
					if (T >= C.From && T <= C.To && C.Samples.Num() < (int32)(ClipSeconds * (Rate / Decimate) + 1))
					{
						C.Samples.Add(Out);
					}
				}
				InDecimate = 0;
				DecimateSum = 0.0;
			}
			if (++InBlock >= BlockFrames)
			{
				if (Blocks.Num() < MaxBlocks)
				{
					FBlock Block;
					Block.T = T;
					Block.Loudness = (float)Db(SumSq / InBlock);
					Block.Peak = (float)(Peak > 1e-5 ? FMath::Max(Floor, 20.0 * FMath::LogX(10.0, Peak)) : Floor);
					for (int32 B = 0; B < Bands; ++B)
					{
						Block.Band[B] = Filters[B].bOn ? (float)Db(BandSq[B] / InBlock) : (float)Floor;
					}
					Blocks.Add(Block);
				}
				else
				{
					bCapped = true;
				}
				InBlock = 0;
				SumSq = Peak = 0.0;
				for (double& V : BandSq)
				{
					V = 0.0;
				}
			}
		}
	}

	TArray<TSharedPtr<FJsonValue>> FMix::SamplesJson()
	{
		FScopeLock Locked(&Lock);
		TArray<TSharedPtr<FJsonValue>> Out;
		Out.Reserve(Blocks.Num());
		auto Round = [](double V) { return FMath::RoundToDouble(V * 10.0) / 10.0; };
		for (const FBlock& B : Blocks)
		{
			const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
			V->SetNumberField(TEXT("loudness"), Round(B.Loudness));
			V->SetNumberField(TEXT("peak"), Round(B.Peak));
			for (int32 I = 0; I < Bands; ++I)
			{
				V->SetNumberField(BandNames[I], Round(B.Band[I]));
			}
			const TSharedRef<FJsonObject> S = MakeShared<FJsonObject>();
			S->SetNumberField(TEXT("t"), FMath::RoundToDouble(B.T * 1000.0) / 1000.0);
			S->SetObjectField(TEXT("value"), V);
			Out.Add(MakeShared<FJsonValueObject>(S));
		}
		return Out;
	}

	TArray<FString> FMix::WriteClips(const FString& Dir)
	{
		FScopeLock Locked(&Lock);
		TArray<FString> Written;
		const int32 ClipHz = Rate > 0 ? Rate / Decimate : 0;
		for (const FClip& C : Clips)
		{
			if (C.Samples.Num() == 0 || ClipHz <= 0)
			{
				continue;
			}
			// a 16-bit mono PCM WAV: its 44-byte header, then the samples (little-endian, as every platform here is)
			const uint32 DataBytes = C.Samples.Num() * sizeof(int16);
			TArray<uint8> Wav;
			Wav.Reserve(44 + DataBytes);
			auto Put32 = [&Wav](uint32 V) { for (int32 I = 0; I < 4; ++I) { Wav.Add((V >> (8 * I)) & 0xFF); } };
			auto Put16 = [&Wav](uint16 V) { Wav.Add(V & 0xFF); Wav.Add(V >> 8); };
			auto Tag = [&Wav](const char* S) { for (int32 I = 0; I < 4; ++I) { Wav.Add((uint8)S[I]); } };
			Tag("RIFF"); Put32(36 + DataBytes); Tag("WAVE");
			Tag("fmt "); Put32(16); Put16(1); Put16(1); Put32(ClipHz); Put32(ClipHz * 2); Put16(2); Put16(16);
			Tag("data"); Put32(DataBytes);
			Wav.Append(reinterpret_cast<const uint8*>(C.Samples.GetData()), DataBytes);
			const FString File = FString::Printf(TEXT("heard_%s.wav"), *C.Name);
			if (FFileHelper::SaveArrayToFile(Wav, *FPaths::Combine(Dir, File)))
			{
				Written.Add(File);
			}
		}
		return Written;
	}
}
