// Free local video assembler for the channel (macOS, no third-party software).
// Usage: ./render project.json [--max SECONDS]
// Reads clips (still images with start/duration/zoom/fade), voice files and optional music,
// renders a silent H.264 video with AVAssetWriter, then muxes audio with AVAssetExportSession.
import AVFoundation
import AppKit
import CoreGraphics
import Foundation

struct Clip: Codable { var image: String; var start: Double; var duration: Double; var zoom: String?; var fade: Double? }
struct Aud: Codable { var file: String; var start: Double; var volume: Float? }
struct Project: Codable {
    var width: Int; var height: Int; var fps: Int
    var clips: [Clip]; var audio: [Aud]; var music: Aud?; var output: String
}

func fail(_ m: String) -> Never { FileHandle.standardError.write((m + "\n").data(using: .utf8)!); exit(1) }

let args = CommandLine.arguments
guard args.count >= 2 else { fail("usage: render project.json [--max SECONDS]") }
let projURL = URL(fileURLWithPath: args[1])
let base = projURL.deletingLastPathComponent()
var maxSeconds: Double? = nil
if let i = args.firstIndex(of: "--max"), i + 1 < args.count { maxSeconds = Double(args[i + 1]) }
guard let data = try? Data(contentsOf: projURL), let proj = try? JSONDecoder().decode(Project.self, from: data) else { fail("cannot read project.json") }

func resolve(_ p: String) -> URL { p.hasPrefix("/") ? URL(fileURLWithPath: p) : URL(fileURLWithPath: ((base.path as NSString).appendingPathComponent(p) as NSString).standardizingPath) }

var total = proj.clips.map { $0.start + $0.duration }.max() ?? 0
if let m = maxSeconds { total = min(total, m) }
let W = proj.width, H = proj.height, fps = proj.fps
let frames = Int((total * Double(fps)).rounded(.up))
let sorted = proj.clips.sorted { $0.start < $1.start }

var cache: [Int: CGImage] = [:]
func image(_ i: Int) -> CGImage {
    if let c = cache[i] { return c }
    if cache.count > 4 { cache.removeAll() }
    let url = resolve(sorted[i].image)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil), let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { fail("cannot load \(url.path)") }
    cache[i] = img
    return img
}

func clipIndex(at t: Double) -> Int {
    var idx = 0
    for (i, c) in sorted.enumerated() where c.start <= t + 1e-6 { idx = i }
    return idx
}

func scale(_ c: Clip, _ t: Double) -> Double {
    let p = min(max((t - c.start) / max(c.duration, 0.001), 0), 1)
    switch c.zoom ?? "none" {
    case "in": return 1.0 + 0.06 * p
    case "out": return 1.06 - 0.06 * p
    default: return 1.0
    }
}

func draw(_ ctx: CGContext, _ img: CGImage, _ s: Double, _ alpha: Double) {
    let w = Double(W) * s, h = Double(H) * s
    ctx.setAlpha(CGFloat(alpha))
    ctx.draw(img, in: CGRect(x: (Double(W) - w) / 2, y: (Double(H) - h) / 2, width: w, height: h))
    ctx.setAlpha(1)
}

let tmpVideo = FileManager.default.temporaryDirectory.appendingPathComponent("silent_\(UUID().uuidString).mp4")
let writer = try AVAssetWriter(outputURL: tmpVideo, fileType: .mp4)
let vInput = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: W, AVVideoHeightKey: H,
    // YouTube upload recommendation (support.google.com/youtube/answer/1722171): H.264 High, progressive,
    // CABAC, B-frames, closed GOP of half the frame rate, 4:2:0, 1080p30 about 8 Mbps (we target 10 for headroom).
    AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: H >= 1440 ? 20_000_000 : 10_000_000, AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
                                      AVVideoH264EntropyModeKey: AVVideoH264EntropyModeCABAC, AVVideoAllowFrameReorderingKey: true,
                                      AVVideoMaxKeyFrameIntervalKey: max(fps / 2, 1), AVVideoQualityKey: H >= 1440 ? 1.0 : 0.95],
])
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: vInput, sourcePixelBufferAttributes: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA, kCVPixelBufferWidthKey as String: W, kCVPixelBufferHeightKey as String: H,
])
vInput.expectsMediaDataInRealTime = false
writer.add(vInput)
guard writer.startWriting() else { fail("writer: \(writer.error?.localizedDescription ?? "?")") }
writer.startSession(atSourceTime: .zero)

let cs = CGColorSpaceCreateDeviceRGB()
for f in 0..<frames {
    while !vInput.isReadyForMoreMediaData { Thread.sleep(forTimeInterval: 0.002) }
    guard let pool = adaptor.pixelBufferPool else { fail("no pixel pool") }
    var pbOpt: CVPixelBuffer?
    CVPixelBufferPoolCreatePixelBuffer(nil, pool, &pbOpt)
    guard let pb = pbOpt else { fail("no pixel buffer") }
    CVPixelBufferLockBaseAddress(pb, [])
    let ctx = CGContext(data: CVPixelBufferGetBaseAddress(pb), width: W, height: H, bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(pb),
                        space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)!
    ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
    let t = Double(f) / Double(fps)
    let i = clipIndex(at: t)
    let c = sorted[i]
    let fade = c.fade ?? 0
    if i > 0 && fade > 0 && t - c.start < fade {
        let p = (t - c.start) / fade
        let prev = sorted[i - 1]
        draw(ctx, image(i - 1), scale(prev, prev.start + prev.duration), 1)
        draw(ctx, image(i), scale(c, t), p)
    } else {
        draw(ctx, image(i), scale(c, t), 1)
    }
    CVPixelBufferUnlockBaseAddress(pb, [])
    adaptor.append(pb, withPresentationTime: CMTime(value: Int64(f), timescale: CMTimeScale(fps)))
    if f % 300 == 0 { print("frame \(f)/\(frames)") }
}
vInput.markAsFinished()
let sem = DispatchSemaphore(value: 0)
writer.finishWriting { sem.signal() }
sem.wait()
guard writer.status == .completed else { fail("video failed: \(writer.error?.localizedDescription ?? "?")") }
print("video done, adding audio")

// audio mux
let comp = AVMutableComposition()
let vAsset = AVURLAsset(url: tmpVideo)
let vSem = DispatchSemaphore(value: 0)
var vTrack: AVAssetTrack?
vAsset.loadTracks(withMediaType: .video) { tr, _ in vTrack = tr?.first; vSem.signal() }
vSem.wait()
guard let srcV = vTrack, let compV = comp.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid) else { fail("no video track") }
try compV.insertTimeRange(CMTimeRange(start: .zero, duration: vAsset.duration), of: srcV, at: .zero)

var params: [AVMutableAudioMixInputParameters] = []
func addAudio(_ a: Aud, defaultVolume: Float) {
    let asset = AVURLAsset(url: resolve(a.file))
    let s = DispatchSemaphore(value: 0)
    var tr: AVAssetTrack?
    asset.loadTracks(withMediaType: .audio) { t, _ in tr = t?.first; s.signal() }
    s.wait()
    guard let src = tr, let dst = comp.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid) else { print("skip audio \(a.file)"); return }
    let start = CMTime(seconds: a.start, preferredTimescale: 600)
    var dur = asset.duration
    if let m = maxSeconds, a.start + dur.seconds > m { dur = CMTime(seconds: max(m - a.start, 0), preferredTimescale: 600) }
    if dur.seconds <= 0 { return }
    try? dst.insertTimeRange(CMTimeRange(start: .zero, duration: dur), of: src, at: start)
    let p = AVMutableAudioMixInputParameters(track: dst)
    p.setVolume(a.volume ?? defaultVolume, at: .zero)
    params.append(p)
}
for a in proj.audio { addAudio(a, defaultVolume: 1.0) }
if let m = proj.music {
    // loop music to cover the video, constant low volume under the voice
    let asset = AVURLAsset(url: resolve(m.file))
    let md = asset.duration.seconds
    if md > 1 {
        var at = m.start
        while at < total {
            addAudio(Aud(file: m.file, start: at, volume: m.volume ?? 0.10), defaultVolume: 0.10)
            at += md
        }
    }
}
let mix = AVMutableAudioMix()
mix.inputParameters = params

// Final mux: copy the H.264 video untouched (no second encode) and encode audio as AAC-LC 48 kHz,
// 128 kbps for mono voice, with the moov atom at the front (fast start).
let out = resolve(proj.output)
try? FileManager.default.removeItem(at: out)
let reader = try AVAssetReader(asset: comp)
reader.timeRange = CMTimeRange(start: .zero, duration: CMTime(seconds: total, preferredTimescale: 600))
let vOut = AVAssetReaderTrackOutput(track: compV, outputSettings: nil)
reader.add(vOut)
let aTracks = comp.tracks(withMediaType: .audio)
var aOut: AVAssetReaderAudioMixOutput? = nil
if !aTracks.isEmpty {
    let o = AVAssetReaderAudioMixOutput(audioTracks: aTracks, audioSettings: [AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: 48000, AVNumberOfChannelsKey: 1,
                                                                            AVLinearPCMBitDepthKey: 16, AVLinearPCMIsFloatKey: false, AVLinearPCMIsBigEndianKey: false, AVLinearPCMIsNonInterleaved: false])
    o.audioMix = mix
    reader.add(o)
    aOut = o
}
let fw = try AVAssetWriter(outputURL: out, fileType: .mp4)
fw.shouldOptimizeForNetworkUse = true
let fmt = (try? await srcV.load(.formatDescriptions))?.first
let vIn = AVAssetWriterInput(mediaType: .video, outputSettings: nil, sourceFormatHint: fmt)
vIn.expectsMediaDataInRealTime = false
fw.add(vIn)
var aIn: AVAssetWriterInput? = nil
if aOut != nil {
    let i = AVAssetWriterInput(mediaType: .audio, outputSettings: [AVFormatIDKey: kAudioFormatMPEG4AAC, AVSampleRateKey: 48000, AVNumberOfChannelsKey: 1, AVEncoderBitRateKey: 128_000])
    i.expectsMediaDataInRealTime = false
    fw.add(i)
    aIn = i
}
guard reader.startReading() else { fail("reader: \(reader.error?.localizedDescription ?? "?")") }
guard fw.startWriting() else { fail("final writer: \(fw.error?.localizedDescription ?? "?")") }
fw.startSession(atSourceTime: .zero)
let group = DispatchGroup()
func pump(_ input: AVAssetWriterInput, _ output: AVAssetReaderOutput, _ label: String) {
    group.enter()
    let q = DispatchQueue(label: label)
    input.requestMediaDataWhenReady(on: q) {
        while input.isReadyForMoreMediaData {
            if let sb = output.copyNextSampleBuffer() { input.append(sb) } else { input.markAsFinished(); group.leave(); return }
        }
    }
}
pump(vIn, vOut, "video")
if let i = aIn, let o = aOut { pump(i, o, "audio") }
group.wait()
let fSem = DispatchSemaphore(value: 0)
fw.finishWriting { fSem.signal() }
fSem.wait()
try? FileManager.default.removeItem(at: tmpVideo)
guard fw.status == .completed else { fail("final write failed: \(fw.error?.localizedDescription ?? reader.error?.localizedDescription ?? "?")") }
print("done: \(out.path)")
