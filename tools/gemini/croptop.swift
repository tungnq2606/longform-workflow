// Keep the top part of an image:  croptop IN.png OUT.png 0.79   (sips crops around the centre, which cut sheet titles)
import AppKit
let a = CommandLine.arguments
let src = NSImage(contentsOfFile: a[1])!
var rect = CGRect(origin: .zero, size: src.size)
let cg = src.cgImage(forProposedRect: &rect, context: nil, hints: nil)!
let keep = Int(Double(cg.height) * Double(a[3])!)
let part = cg.cropping(to: CGRect(x: 0, y: 0, width: cg.width, height: keep))!   // CGImage origin is top-left
let rep = NSBitmapImageRep(cgImage: part)
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: a[2]))
