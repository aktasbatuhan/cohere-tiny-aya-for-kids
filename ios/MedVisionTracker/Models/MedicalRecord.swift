import Foundation
import SwiftData
import SwiftUI

@Model
final class MedicalRecord {
    var id: UUID
    var timestamp: Date
    var imageData: Data
    var thumbnailData: Data?
    var imageType: String
    var notes: String
    var analysisJSON: String?
    var isFavorite: Bool

    init(
        id: UUID = UUID(),
        timestamp: Date = Date(),
        imageData: Data,
        thumbnailData: Data? = nil,
        imageType: ImageType = .chestXRay,
        notes: String = "",
        analysisResult: AnalysisResult? = nil,
        isFavorite: Bool = false
    ) {
        self.id = id
        self.timestamp = timestamp
        self.imageData = imageData
        self.thumbnailData = thumbnailData
        self.imageType = imageType.rawValue
        self.notes = notes
        self.isFavorite = isFavorite

        if let result = analysisResult {
            self.analysisJSON = try? String(data: JSONEncoder().encode(result), encoding: .utf8)
        }
    }

    var medicalImageType: ImageType {
        get { ImageType(rawValue: imageType) ?? .other }
        set { imageType = newValue.rawValue }
    }

    var analysisResult: AnalysisResult? {
        get {
            guard let json = analysisJSON,
                  let data = json.data(using: .utf8) else { return nil }
            return try? JSONDecoder().decode(AnalysisResult.self, from: data)
        }
        set {
            if let result = newValue {
                analysisJSON = try? String(data: JSONEncoder().encode(result), encoding: .utf8)
            } else {
                analysisJSON = nil
            }
        }
    }

    var image: UIImage? {
        UIImage(data: imageData)
    }

    var thumbnail: UIImage? {
        if let data = thumbnailData {
            return UIImage(data: data)
        }
        return image?.preparingThumbnail(of: CGSize(width: 100, height: 100))
    }
}

enum ImageType: String, Codable, CaseIterable, Identifiable {
    case chestXRay = "Chest X-Ray"
    case abdominalXRay = "Abdominal X-Ray"
    case ctScan = "CT Scan"
    case mriScan = "MRI Scan"
    case ultrasound = "Ultrasound"
    case mammogram = "Mammogram"
    case other = "Other"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .chestXRay, .abdominalXRay: return "rays"
        case .ctScan: return "brain.head.profile"
        case .mriScan: return "brain"
        case .ultrasound: return "waveform.path.ecg"
        case .mammogram: return "circle.grid.cross"
        case .other: return "doc.text.image"
        }
    }
}

struct AnalysisResult: Codable, Equatable {
    let id: UUID
    let timestamp: Date
    let findings: [MedicalFinding]
    let anatomicalLocations: [AnatomicalLocation]
    let overallConfidence: Double
    let summary: String
    let detailedAnalysis: String
    let recommendations: [String]
    let processingTimeSeconds: Double
    let modelVersion: String

    init(
        id: UUID = UUID(),
        timestamp: Date = Date(),
        findings: [MedicalFinding],
        anatomicalLocations: [AnatomicalLocation],
        overallConfidence: Double,
        summary: String,
        detailedAnalysis: String = "",
        recommendations: [String],
        processingTimeSeconds: Double,
        modelVersion: String = "MedGemma-1.5-4B"
    ) {
        self.id = id
        self.timestamp = timestamp
        self.findings = findings
        self.anatomicalLocations = anatomicalLocations
        self.overallConfidence = overallConfidence
        self.summary = summary
        self.detailedAnalysis = detailedAnalysis
        self.recommendations = recommendations
        self.processingTimeSeconds = processingTimeSeconds
        self.modelVersion = modelVersion
    }
}

struct MedicalFinding: Codable, Identifiable, Equatable {
    let id: UUID
    let category: String
    let description: String
    let severity: Severity
    let location: String?
    let confidence: Double

    init(
        id: UUID = UUID(),
        category: String = "General",
        description: String,
        severity: Severity,
        location: String? = nil,
        confidence: Double
    ) {
        self.id = id
        self.category = category
        self.description = description
        self.severity = severity
        self.location = location
        self.confidence = confidence
    }

    enum Severity: String, Codable, CaseIterable {
        case normal = "Normal"
        case mild = "Mild"
        case moderate = "Moderate"
        case severe = "Severe"
        case critical = "Critical"

        var color: Color {
            switch self {
            case .normal: return .green
            case .mild: return .yellow
            case .moderate: return .orange
            case .severe: return .red
            case .critical: return .purple
            }
        }

        var priority: Int {
            switch self {
            case .normal: return 0
            case .mild: return 1
            case .moderate: return 2
            case .severe: return 3
            case .critical: return 4
            }
        }
    }
}

struct AnatomicalLocation: Codable, Identifiable, Equatable {
    let id: UUID
    let name: String
    let boundingBox: NormalizedRect
    let confidence: Double
    let status: String?

    init(
        id: UUID = UUID(),
        name: String,
        boundingBox: NormalizedRect,
        confidence: Double,
        status: String? = nil
    ) {
        self.id = id
        self.name = name
        self.boundingBox = boundingBox
        self.confidence = confidence
        self.status = status
    }
}

struct NormalizedRect: Codable, Equatable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double

    var cgRect: CGRect {
        CGRect(x: x, y: y, width: width, height: height)
    }

    func scaled(to size: CGSize) -> CGRect {
        CGRect(
            x: x * size.width,
            y: y * size.height,
            width: width * size.width,
            height: height * size.height
        )
    }
}