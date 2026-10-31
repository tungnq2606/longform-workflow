// Join two clips with a short cross-dissolve (video and audio), high-bitrate H.264.
// Usage: swift xfade.swift A.mp4 B.mp4 OUT.mp4 [overlapFrames=8] [fps=24] [framesOfA=all] [mbps=60] [skipFramesOfB=0]
// Pass "-" to keep a default. Same file as A and B + framesOfA/skipFramesOfB turns a jolt inside one clip into a short dissolve.
// framesOfA keeps only the first N frames of clip A (drops Veo's jolt near its end).
// mbps: output bitrate; ~3x the source keeps re-encoding loss invisible.
import AVFoundation

let args = CommandLine.arguments
func arg(_ i: Int) -> String? { args.count > i && args[i] != "-" ? args[i] : nil }
let u1 = URL(fileURLWithPath: args[1]), u2 = URL(fileURLWithPath: args[2])
let out = URL(fileURLWithPath: args[3])
let fps = Int32(arg(5) ?? "24")!
let overlap = CMTime(value: Int64(arg(4) ?? "8")!, timescale: fps)
let mbps = Int(arg(7) ?? "60")!
try? FileManager.default.removeItem(at: out)

let a1 = AVURLAsset(url: u1), a2 = AVURLAsset(url: u2)
let d1 = arg(6).map { CMTime(value: Int64($0)!, timescale: fps) } ?? a1.duration
// optional 8th arg: skip the first N frames of clip B (to cut one clip at a jolt, pass the same file twice)
let skipB = CMTime(value: Int64(arg(8) ?? "0")!, timescale: fps)
let d2 = CMTimeSubtract(a2.duration, skipB)
let start2 = CMTimeSubtract(d1, overlap)
let end = CMTimeAdd(start2, d2)
let fadeRange = CMTimeRange(start: start2, duration: overlap)

let comp = AVMutableComposition()
let v1 = comp.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)!
let v2 = comp.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)!
try v1.insertTimeRange(CMTimeRange(start: .zero, duration: d1), of: a1.tracks(withMediaType: .video)[0], at: .zero)
try v2.insertTimeRange(CMTimeRange(start: skipB, duration: d2), of: a2.tracks(withMediaType: .video)[0], at: start2)

var audioTracks: [AVCompositionTrack] = []
let audioMix = AVMutableAudioMix()
if let s1 = a1.tracks(withMediaType: .audio).first, let s2 = a2.tracks(withMediaType: .audio).first {
    let t1 = comp.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)!
    let t2 = comp.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)!
    try t1.insertTimeRange(CMTimeRange(start: .zero, duration: d1), of: s1, at: .zero)
    try t2.insertTimeRange(CMTimeRange(start: skipB, duration: d2), of: s2, at: start2)
    let p1 = AVMutableAudioMixInputParameters(track: t1)
    p1.setVolumeRamp(fromStartVolume: 1, toEndVolume: 0, timeRange: fadeRange)
    let p2 = AVMutableAudioMixInputParameters(track: t2)
    p2.setVolumeRamp(fromStartVolume: 0, toEndVolume: 1, timeRange: fadeRange)
    audioMix.inputParameters = [p1, p2]
    audioTracks = [t1, t2]
}

func instruction(_ range: CMTimeRange, _ layers: [AVMutableVideoCompositionLayerInstruction]) -> AVMutableVideoCompositionInstruction {
    let i = AVMutableVideoCompositionInstruction()
    i.timeRange = range
    i.layerInstructions = layers
    return i
}
let l1 = AVMutableVideoCompositionLayerInstruction(assetTrack: v1)
l1.setOpacityRamp(fromStartOpacity: 1, toEndOpacity: 0, timeRange: fadeRange)
let size = a1.tracks(withMediaType: .video)[0].naturalSize
// Keep clip A's color tags end to end (Veo files: BT.709 primaries, sRGB transfer, BT.601 matrix);
// forcing other tags makes AVFoundation convert and the picture darkens.
let fmt = a1.tracks(withMediaType: .video)[0].formatDescriptions.first as! CMFormatDescription
func tag(_ key: CFString, _ fallback: String) -> String {
    (CMFormatDescriptionGetExtension(fmt, extensionKey: key) as? String) ?? fallback
}
let primaries = tag(kCVImageBufferColorPrimariesKey, AVVideoColorPrimaries_ITU_R_709_2)
let transfer = tag(kCVImageBufferTransferFunctionKey, AVVideoTransferFunction_ITU_R_709_2)
let matrix = tag(kCVImageBufferYCbCrMatrixKey, AVVideoYCbCrMatrix_ITU_R_709_2)
let vc = AVMutableVideoComposition()
vc.renderSize = size
vc.frameDuration = CMTime(value: 1, timescale: fps)
vc.colorPrimaries = primaries
vc.colorTransferFunction = transfer
vc.colorYCbCrMatrix = matrix
vc.instructions = [
    instruction(CMTimeRange(start: .zero, duration: start2), [AVMutableVideoCompositionLayerInstruction(assetTrack: v1)]),
    instruction(fadeRange, [l1, AVMutableVideoCompositionLayerInstruction(assetTrack: v2)]),
    instruction(CMTimeRange(start: d1, end: end), [AVMutableVideoCompositionLayerInstruction(assetTrack: v2)]),
]

// Read the composed frames and write them with a fixed high bitrate.
let reader = try AVAssetReader(asset: comp)
reader.timeRange = CMTimeRange(start: .zero, end: end)
let vOut = AVAssetReaderVideoCompositionOutput(videoTracks: [v1, v2], videoSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange])
vOut.videoComposition = vc
reader.add(vOut)
var aOut: AVAssetReaderAudioMixOutput?
if !audioTracks.isEmpty {
    let o = AVAssetReaderAudioMixOutput(audioTracks: audioTracks, audioSettings: [AVFormatIDKey: kAudioFormatLinearPCM])
    o.audioMix = audioMix
    reader.add(o)
    aOut = o
}

let writer = try AVAssetWriter(outputURL: out, fileType: .mp4)
let vIn = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: Int(size.width), AVVideoHeightKey: Int(size.height),
    AVVideoColorPropertiesKey: [
        AVVideoColorPrimariesKey: primaries,
        AVVideoTransferFunctionKey: transfer,
        AVVideoYCbCrMatrixKey: matrix],
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: mbps * 1_000_000,
        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
        AVVideoMaxKeyFrameIntervalKey: Int(fps)]])
vIn.expectsMediaDataInRealTime = false
writer.add(vIn)
var aIn: AVAssetWriterInput?
if aOut != nil {
    let i = AVAssetWriterInput(mediaType: .audio, outputSettings: [
        AVFormatIDKey: kAudioFormatMPEG4AAC, AVNumberOfChannelsKey: 2,
        AVSampleRateKey: 48000, AVEncoderBitRateKey: 256_000])
    writer.add(i)
    aIn = i
}

writer.startWriting()
reader.startReading()
writer.startSession(atSourceTime: .zero)
let group = DispatchGroup()
func pump(_ input: AVAssetWriterInput, _ output: AVAssetReaderOutput, _ label: String) {
    group.enter()
    let q = DispatchQueue(label: label)
    input.requestMediaDataWhenReady(on: q) {
        while input.isReadyForMoreMediaData {
            if let buf = output.copyNextSampleBuffer() { input.append(buf) }
            else { input.markAsFinished(); group.leave(); return }
        }
    }
}
pump(vIn, vOut, "video")
if let aIn, let aOut { pump(aIn, aOut, "audio") }
group.wait()
let sem = DispatchSemaphore(value: 0)
writer.finishWriting { sem.signal() }
sem.wait()
if writer.status == .completed && reader.status != .failed {
    print("OK", out.path, CMTimeGetSeconds(end), "s,", mbps, "Mbps")
} else {
    print("FAILED", writer.error ?? reader.error ?? "unknown"); exit(1)
}
