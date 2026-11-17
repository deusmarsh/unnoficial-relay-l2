import AppKit
import Foundation

// Original geometric artwork; no game or publisher assets.
let output = URL(fileURLWithPath:CommandLine.arguments[1],isDirectory:true)
try FileManager.default.createDirectory(at:output,withIntermediateDirectories:true)
for role in ["Relay","Runtime"] {
    let iconset = output.appendingPathComponent(role + ".iconset",isDirectory:true)
    try FileManager.default.createDirectory(at:iconset,withIntermediateDirectories:true)
    for size in [16,32,128,256,512] {
        for scale in [1,2] {
            let pixels = size * scale
            let rep = NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:pixels,pixelsHigh:pixels,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
            let context = NSGraphicsContext(bitmapImageRep:rep)!
            NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = context
            context.cgContext.scaleBy(x:CGFloat(pixels)/1024,y:CGFloat(pixels)/1024)
            let tile = NSBezierPath(roundedRect:NSRect(x:100,y:100,width:824,height:824),xRadius:184,yRadius:184)
            NSColor(calibratedRed:0.08,green:0.11,blue:0.18,alpha:1).setFill();tile.fill()
            NSColor(calibratedRed:0.28,green:0.72,blue:0.88,alpha:1).setStroke()
            let glyph = NSBezierPath();glyph.lineWidth = 62;glyph.lineCapStyle = .round;glyph.lineJoinStyle = .round
            if role == "Relay" {
                glyph.move(to:NSPoint(x:360,y:705));glyph.line(to:NSPoint(x:360,y:335));glyph.line(to:NSPoint(x:665,y:335))
                let dot = NSBezierPath(ovalIn:NSRect(x:613,y:636,width:84,height:84));NSColor(calibratedRed:0.28,green:0.72,blue:0.88,alpha:1).setFill();dot.fill()
            } else {
                glyph.move(to:NSPoint(x:400,y:680));glyph.line(to:NSPoint(x:265,y:512));glyph.line(to:NSPoint(x:400,y:344))
                glyph.move(to:NSPoint(x:624,y:680));glyph.line(to:NSPoint(x:759,y:512));glyph.line(to:NSPoint(x:624,y:344))
            }
            glyph.stroke();NSGraphicsContext.restoreGraphicsState()
            let suffix = scale == 2 ? "@2x" : ""
            try rep.representation(using:.png,properties:[:])!.write(to:iconset.appendingPathComponent("icon_\(size)x\(size)\(suffix).png"))
        }
    }
}
