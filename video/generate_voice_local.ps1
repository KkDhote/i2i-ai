param([int]$OnlyScene = 0)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$videoProgressCode = @'
using System;
using System.Collections.Generic;
using System.Speech.Synthesis;
public class VideoSpeechWords {
    public List<string> Rows = new List<string>();
    public void Capture(object sender, SpeakProgressEventArgs e) {
        string safe = e.Text.Replace("\t", " ").Replace("\n", " ").Replace("\r", " ");
        Rows.Add(e.AudioPosition.TotalSeconds.ToString(System.Globalization.CultureInfo.InvariantCulture) + "\t" + safe);
    }
    public void Connect(SpeechSynthesizer synth) { synth.SpeakProgress += Capture; }
}
'@
Add-Type -TypeDefinition $videoProgressCode -ReferencedAssemblies @('System.Speech', 'System.Runtime', 'System.Collections')
$videoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$videoScenes = Get-Content -Raw -LiteralPath (Join-Path $videoRoot 'storyboard.json') -Encoding UTF8 | ConvertFrom-Json
if ($OnlyScene -gt 0) { $videoScenes = $videoScenes | Where-Object { [int]$_.id -eq $OnlyScene } }
$videoAudioDir = Join-Path $videoRoot 'audio'
New-Item -ItemType Directory -Force -Path $videoAudioDir | Out-Null
$videoSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$videoProgress = New-Object VideoSpeechWords
$videoProgress.Connect($videoSynth)
try {
    $videoSynth.SelectVoice('Microsoft David')
    $videoSynth.Rate = 0
    $videoSynth.Volume = 100
    foreach ($videoScene in $videoScenes) {
        $videoProgress.Rows.Clear()
        $videoFile = Join-Path $videoAudioDir ('scene-{0:00}.wav' -f [int]$videoScene.id)
        $videoFormat = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
        $videoSynth.SetOutputToWaveFile($videoFile, $videoFormat)
        $videoText = [System.Security.SecurityElement]::Escape($videoScene.narration)
        $videoSsml = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US"><prosody pitch="-12%">' + $videoText + '</prosody></speak>'
        $videoSynth.SpeakSsml($videoSsml)
        $videoSynth.SetOutputToNull()
        $videoProgress.Rows | Set-Content -LiteralPath (Join-Path $videoAudioDir ('words-{0:00}.tsv' -f [int]$videoScene.id)) -Encoding UTF8
        Write-Output ('Generated local narration: ' + $videoScene.id)
    }
} finally {
    $videoSynth.Dispose()
}
$videoMeta = [ordered]@{
    provider = 'Microsoft Windows on-device speech synthesis'
    voice = 'Microsoft David'
    style = 'Male voice; SSML pitch -12%; normal speech rate; explicit 16 kHz output'
    generated_speech = $true
    cloud_upload = $false
}
$videoMeta | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $videoRoot 'voice-metadata.json') -Encoding UTF8
