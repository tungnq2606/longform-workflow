// Assemble several clips in order, each with an in/out frame range and an optional
// cross-dissolve into it (video and audio), written as high-bitrate H.264.
// Usage: swift assemble.swift spec.json
// spec.json: {"out": "OUT.mp4", "fps": 24, "mbps": 60,
//             "muteClips": true, "audio": [{"file": "voice.mp3", "at": 0, "volume": 1}],
//             optional "width"/"height" = output size (scaled from the first clip's size),
//             "clips": [{"file": "A.mp4", "in": 0, "out": 127, "xfade": 0}, ...]}
// "in"/"out" are frame numbers (out exclusive); "xfade" = frames of dissolve from the
// previous clip into this one (0 = hard cut); optional "freeze" = frames to hold the "in"
// frame as a still before the clip plays (with a slow zoom-out, "holdZoom" in the spec,
// default 1.06). Color tags are copied from the first clip. Audio entries may add "start"
// (seconds into the file) and "fadeOut" (seconds of fade to silence at the video's end).
import AVFoundation

struct Clip: Decodable { let file: String; let `in`: Int; let out: Int; let xfade: Int?; let freeze: Int? }
struct Extra: Decodable { let file: String; let at: Double?; let volume: Float?; let start: Double?; let fadeOut: Double? }
struct Spec: Decodable {
    let out: String; let fps: Int32?; let mbps: Int?; let holdZoom: Double?; let clips: [Clip]
    let width: Int?; let height: Int?
    let muteClips: Bool?   // true = drop the clips' own sound
    let audio: [Extra]?    // extra audio files (voice-over, music) placed at "at" seconds
}

let spec = try JSONDecoder().decode(Spec.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
let fps = spec.fps ?? 24, mbps = spec.mbps ?? 60
func t(_ frames: Int) -> CMTime { CMTime(value: Int64(frames), timescale: fps) }
let out = URL(fileURLWithPath: spec.out)
try? FileManager.default.removeItem(at: out)

let comp = AVMutableComposition()
let vTracks = (0..<2).map { _ in comp.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)! }
let aTracks = (0..<2).map { _ in comp.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)! }

// Place clips: clip i starts xfade(i) frames before clip i-1 ends, alternating tracks.
var starts: [Int] = [], ends: [Int] = []
var firstAsset: AVURLAsset?
for (i, c) in spec.clips.enumerated() {
    let asset = AVURLAsset(url: URL(fileURLWithPath: c.file))
    if firstAsset == nil { firstAsset = asset }
    let start = i == 0 ? 0 : ends[i - 1] - (c.xfade ?? 0)
    let hold = c.freeze ?? 0
    let video = asset.tracks(withMediaType: .video)[0]
    if hold > 0 {
        // Hold the "in" frame as a still for `hold` frames (silent), then play the clip.
        // One real frame per slot (not scaleTimeRange) so the output stays constant 24 fps.
        for k in 0..<hold {
            try vTracks[i % 2].insertTimeRange(CMTimeRange(start: t(c.in), duration: t(1)), of: video, at: t(start + k))
        }
    }
    let range = CMTimeRange(start: t(c.in), duration: t(c.out - c.in))
    try vTracks[i % 2].insertTimeRange(range, of: video, at: t(start + hold))
    if !(spec.muteClips ?? false), let a = asset.tracks(withMediaType: .audio).first {
        try aTracks[i % 2].insertTimeRange(range, of: a, at: t(start + hold))
    }
    starts.append(start)
    ends.append(start + hold + c.out - c.in)
}
let total = ends.last!

// Extra audio (voice-over, music): whole file at its start time, cut at the video's end.
var extraTracks: [AVMutableCompositionTrack] = []
var extraParams: [AVMutableAudioMixInputParameters] = []
for e in spec.audio ?? [] {
    let asset = AVURLAsset(url: URL(fileURLWithPath: e.file))
    guard let src = asset.tracks(withMediaType: .audio).first else { continue }
    let at = CMTime(seconds: e.at ?? 0, preferredTimescale: 48000)
    let room = CMTimeSubtract(t(total), at)
    guard room > .zero else { continue }
    let tr = comp.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)!
    let from = CMTime(seconds: e.start ?? 0, preferredTimescale: 48000)
    try tr.insertTimeRange(CMTimeRange(start: from, duration: CMTimeMinimum(CMTimeSubtract(asset.duration, from), room)), of: src, at: at)
    let p = AVMutableAudioMixInputParameters(track: tr)
    let vol = e.volume ?? 1
    p.setVolume(vol, at: .zero)
    if let f = e.fadeOut, f > 0 {
        let fadeStart = CMTimeMaximum(at, CMTimeSubtract(t(total), CMTime(seconds: f, preferredTimescale: 48000)))
        p.setVolumeRamp(fromStartVolume: vol, toEndVolume: 0, timeRange: CMTimeRange(start: fadeStart, end: t(total)))
    }
    extraTracks.append(tr)
    extraParams.append(p)
}

// Held stills slowly zoom out from holdZoom to 100%, so a still never sits dead.
let canvas = firstAsset!.tracks(withMediaType: .video)[0].naturalSize
// Output size: the first clip's size unless the spec gives width/height (all clips share it).
let size = CGSize(width: CGFloat(spec.width ?? Int(canvas.width)), height: CGFloat(spec.height ?? Int(canvas.height)))
let scale = size.width / canvas.width
let holdZoom = CGFloat(spec.holdZoom ?? 1.06)
// The zoom runs on through the whole clip and only reaches 100% at its last frame: stopping
// a zoom mid-shot shows as a small jolt (motion stops, resampling sharpness changes).
func zoomEnd(_ i: Int) -> Int {
    (spec.clips[i].freeze ?? 0) == 0 ? starts[i] : ends[i]
}
func zoom(_ i: Int, _ frame: Int) -> CGFloat {
    let hs = starts[i], ze = zoomEnd(i)
    if frame >= ze || ze == hs { return 1 }
    return holdZoom + (1 - holdZoom) * CGFloat(max(frame, hs) - hs) / CGFloat(ze - hs)
}
func centered(_ z: CGFloat) -> CGAffineTransform {
    CGAffineTransform(a: z * scale, b: 0, c: 0, d: z * scale,
                      tx: (1 - z) * size.width / 2, ty: (1 - z) * size.height / 2)
}
func layer(_ i: Int, _ from: Int, _ to: Int) -> AVMutableVideoCompositionLayerInstruction {
    let l = AVMutableVideoCompositionLayerInstruction(assetTrack: vTracks[i % 2])
    let ze = zoomEnd(i)
    if from < ze {
        let a = max(from, starts[i]), b = min(to, ze)
        l.setTransformRamp(fromStart: centered(zoom(i, a)), toEnd: centered(zoom(i, b)),
                           timeRange: CMTimeRange(start: t(a), end: t(b)))
        if b < to { l.setTransform(centered(1), at: t(b)) }
    } else {
        l.setTransform(centered(1), at: t(from))
    }
    return l
}

// Video instructions: solo stretches and dissolves; audio: matching volume ramps.
var instructions: [AVMutableVideoCompositionInstruction] = []
let audioParams = aTracks.map { AVMutableAudioMixInputParameters(track: $0) }
func solo(_ i: Int, _ from: Int, _ to: Int) {
    guard to > from else { return }
    let ins = AVMutableVideoCompositionInstruction()
    ins.timeRange = CMTimeRange(start: t(from), end: t(to))
    ins.layerInstructions = [layer(i, from, to)]
    instructions.append(ins)
}
for i in spec.clips.indices {
    let inFade = i == 0 ? 0 : (spec.clips[i].xfade ?? 0)
    let outFade = i + 1 < spec.clips.count ? (spec.clips[i + 1].xfade ?? 0) : 0
    solo(i, starts[i] + inFade, ends[i] - outFade)
    if outFade > 0 {
        let r = CMTimeRange(start: t(ends[i] - outFade), end: t(ends[i]))
        let top = layer(i, ends[i] - outFade, ends[i])
        // Reach 0 one frame early: the last dissolve frame is then clean clip B, with no jump
        // into the solo stretch that follows.
        top.setOpacityRamp(fromStartOpacity: 1, toEndOpacity: 0,
                           timeRange: CMTimeRange(start: t(ends[i] - outFade), end: t(ends[i] - 1)))
        let ins = AVMutableVideoCompositionInstruction()
        ins.timeRange = r
        ins.layerInstructions = [top, layer(i + 1, ends[i] - outFade, ends[i])]
        instructions.append(ins)
        audioParams[i % 2].setVolumeRamp(fromStartVolume: 1, toEndVolume: 0, timeRange: r)
        audioParams[(i + 1) % 2].setVolumeRamp(fromStartVolume: 0, toEndVolume: 1, timeRange: r)
    }
}

let src = firstAsset!.tracks(withMediaType: .video)[0]
let fmt = src.formatDescriptions.first as! CMFormatDescription
func tag(_ key: CFString, _ fallback: String) -> String {
    (CMFormatDescriptionGetExtension(fmt, extensionKey: key) as? String) ?? fallback
}
let primaries = tag(kCVImageBufferColorPrimariesKey, AVVideoColorPrimaries_ITU_R_709_2)
let transfer = tag(kCVImageBufferTransferFunctionKey, AVVideoTransferFunction_ITU_R_709_2)
let matrix = tag(kCVImageBufferYCbCrMatrixKey, AVVideoYCbCrMatrix_ITU_R_709_2)
let vc = AVMutableVideoComposition()
vc.renderSize = size
vc.frameDuration = t(1)
vc.colorPrimaries = primaries
vc.colorTransferFunction = transfer
vc.colorYCbCrMatrix = matrix
vc.instructions = instructions
let mix = AVMutableAudioMix()
mix.inputParameters = audioParams + extraParams

let reader = try AVAssetReader(asset: comp)
reader.timeRange = CMTimeRange(start: .zero, end: t(total))
let vOut = AVAssetReaderVideoCompositionOutput(videoTracks: vTracks, videoSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange])
vOut.videoComposition = vc
reader.add(vOut)
let aOut = AVAssetReaderAudioMixOutput(audioTracks: aTracks.filter { !$0.segments.isEmpty } + extraTracks,
                                       audioSettings: [AVFormatIDKey: kAudioFormatLinearPCM])
aOut.audioMix = mix
reader.add(aOut)

let writer = try AVAssetWriter(outputURL: out, fileType: .mp4)
let vIn = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: Int(size.width), AVVideoHeightKey: Int(size.height),
    AVVideoColorPropertiesKey: [AVVideoColorPrimariesKey: primaries,
                                AVVideoTransferFunctionKey: transfer,
                                AVVideoYCbCrMatrixKey: matrix],
    AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: mbps * 1_000_000,
                                      AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
                                      AVVideoMaxKeyFrameIntervalKey: Int(fps)]])
vIn.expectsMediaDataInRealTime = false
let aIn = AVAssetWriterInput(mediaType: .audio, outputSettings: [
    AVFormatIDKey: kAudioFormatMPEG4AAC, AVNumberOfChannelsKey: 2,
    AVSampleRateKey: 48000, AVEncoderBitRateKey: 256_000])
writer.add(vIn)
writer.add(aIn)
// The adaptor must exist before writing starts.
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: vIn, sourcePixelBufferAttributes: nil)

writer.startWriting()
reader.startReading()
writer.startSession(atSourceTime: .zero)
let group = DispatchGroup()
func pump(_ input: AVAssetWriterInput, _ output: AVAssetReaderOutput, _ label: String) {
    group.enter()
    input.requestMediaDataWhenReady(on: DispatchQueue(label: label)) {
        while input.isReadyForMoreMediaData {
            if let buf = output.copyNextSampleBuffer() { input.append(buf) }
            else { input.markAsFinished(); group.leave(); return }
        }
    }
}
// Video at constant frame rate: the compositor skips repeated frames (held stills), so
// re-emit the last picture for every missing frame slot up to the end.
func pumpVideo() {
    group.enter()
    var next = 0
    var last: CVPixelBuffer?
    var pending: (CVPixelBuffer, Int)?
    vIn.requestMediaDataWhenReady(on: DispatchQueue(label: "video")) {
        while vIn.isReadyForMoreMediaData {
            if pending == nil {
                if let buf = vOut.copyNextSampleBuffer() {
                    guard let px = CMSampleBufferGetImageBuffer(buf) else { continue }
                    let pts = CMSampleBufferGetPresentationTimeStamp(buf)
                    pending = (px, Int((CMTimeGetSeconds(pts) * Double(fps)).rounded()))
                } else if let l = last, next < total {
                    adaptor.append(l, withPresentationTime: t(next)); next += 1; continue
                } else {
                    vIn.markAsFinished(); group.leave(); return
                }
            }
            let (px, idx) = pending!
            if idx < next { pending = nil; continue }
            if idx > next, let l = last { adaptor.append(l, withPresentationTime: t(next)); next += 1; continue }
            adaptor.append(px, withPresentationTime: t(idx))
            last = px; next = idx + 1; pending = nil
        }
    }
}
pumpVideo()
pump(aIn, aOut, "audio")
group.wait()
let sem = DispatchSemaphore(value: 0)
writer.finishWriting { sem.signal() }
sem.wait()
if writer.status == .completed && reader.status != .failed {
    print("OK", out.path, Double(total) / Double(fps), "s,", mbps, "Mbps")
} else {
    print("FAILED", writer.error ?? reader.error ?? "unknown"); exit(1)
}
