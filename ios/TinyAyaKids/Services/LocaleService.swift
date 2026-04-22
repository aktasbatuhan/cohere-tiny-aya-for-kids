import Foundation
import Observation

/// User-selectable languages for Aya conversations.
/// Scoped to the 22 TinyAya-supported languages.
enum AyaLanguage: String, CaseIterable, Identifiable, Codable {
    case english = "en"
    case turkish = "tr"
    case spanish = "es"
    case french = "fr"
    case german = "de"
    case italian = "it"
    case portuguese = "pt"
    case dutch = "nl"
    case polish = "pl"
    case czech = "cs"
    case romanian = "ro"
    case russian = "ru"
    case ukrainian = "uk"
    case arabic = "ar"
    case hindi = "hi"
    case indonesian = "id"
    case japanese = "ja"
    case korean = "ko"
    case chinese = "zh"
    case vietnamese = "vi"
    case swahili = "sw"
    case thai = "th"
    case telugu = "te"

    var id: String { rawValue }

    /// Native-language label used in the language picker (so a German
    /// speaker sees "Deutsch", not "German").
    var nativeName: String {
        switch self {
        case .english:     return "English"
        case .turkish:     return "Türkçe"
        case .spanish:     return "Español"
        case .french:      return "Français"
        case .german:      return "Deutsch"
        case .italian:     return "Italiano"
        case .portuguese:  return "Português"
        case .dutch:       return "Nederlands"
        case .polish:      return "Polski"
        case .czech:       return "Čeština"
        case .romanian:    return "Română"
        case .russian:     return "Русский"
        case .ukrainian:   return "Українська"
        case .arabic:      return "العربية"
        case .hindi:       return "हिन्दी"
        case .indonesian:  return "Bahasa Indonesia"
        case .japanese:    return "日本語"
        case .korean:      return "한국어"
        case .chinese:     return "中文"
        case .vietnamese:  return "Tiếng Việt"
        case .swahili:     return "Kiswahili"
        case .thai:        return "ไทย"
        case .telugu:      return "తెలుగు"
        }
    }

    /// English name used in prompts to the LLM.
    var englishName: String {
        switch self {
        case .english:     return "English"
        case .turkish:     return "Turkish"
        case .spanish:     return "Spanish"
        case .french:      return "French"
        case .german:      return "German"
        case .italian:     return "Italian"
        case .portuguese:  return "Portuguese"
        case .dutch:       return "Dutch"
        case .polish:      return "Polish"
        case .czech:       return "Czech"
        case .romanian:    return "Romanian"
        case .russian:     return "Russian"
        case .ukrainian:   return "Ukrainian"
        case .arabic:      return "Arabic"
        case .hindi:       return "Hindi"
        case .indonesian:  return "Indonesian"
        case .japanese:    return "Japanese"
        case .korean:      return "Korean"
        case .chinese:     return "Chinese"
        case .vietnamese:  return "Vietnamese"
        case .swahili:     return "Swahili"
        case .thai:        return "Thai"
        case .telugu:      return "Telugu"
        }
    }

    var flag: String {
        switch self {
        case .english:     return "🇺🇸"
        case .turkish:     return "🇹🇷"
        case .spanish:     return "🇪🇸"
        case .french:      return "🇫🇷"
        case .german:      return "🇩🇪"
        case .italian:     return "🇮🇹"
        case .portuguese:  return "🇵🇹"
        case .dutch:       return "🇳🇱"
        case .polish:      return "🇵🇱"
        case .czech:       return "🇨🇿"
        case .romanian:    return "🇷🇴"
        case .russian:     return "🇷🇺"
        case .ukrainian:   return "🇺🇦"
        case .arabic:      return "🇦🇪"
        case .hindi:       return "🇮🇳"
        case .indonesian:  return "🇮🇩"
        case .japanese:    return "🇯🇵"
        case .korean:      return "🇰🇷"
        case .chinese:     return "🇨🇳"
        case .vietnamese:  return "🇻🇳"
        case .swahili:     return "🇰🇪"
        case .thai:        return "🇹🇭"
        case .telugu:      return "🇮🇳"
        }
    }

    /// True if Kokoro TTS natively supports this language (en only as of v1.0).
    /// Other languages fall back to AVSpeechSynthesizer.
    var usesKokoroTTS: Bool {
        self == .english
    }

    /// BCP-47 locale identifier for AVSpeechSynthesizer voice lookup.
    var speechVoiceIdentifier: String {
        switch self {
        case .english:     return "en-US"
        case .turkish:     return "tr-TR"
        case .spanish:     return "es-ES"
        case .french:      return "fr-FR"
        case .german:      return "de-DE"
        case .italian:     return "it-IT"
        case .portuguese:  return "pt-PT"
        case .dutch:       return "nl-NL"
        case .polish:      return "pl-PL"
        case .czech:       return "cs-CZ"
        case .romanian:    return "ro-RO"
        case .russian:     return "ru-RU"
        case .ukrainian:   return "uk-UA"
        case .arabic:      return "ar-SA"
        case .hindi:       return "hi-IN"
        case .indonesian:  return "id-ID"
        case .japanese:    return "ja-JP"
        case .korean:      return "ko-KR"
        case .chinese:     return "zh-CN"
        case .vietnamese:  return "vi-VN"
        case .swahili:     return "sw-KE"
        case .thai:        return "th-TH"
        case .telugu:      return "te-IN"
        }
    }

    /// Prompt fragment instructing the model to respond in this language.
    /// English returns empty — avoids polluting the default prompt.
    var responseLanguageInstruction: String {
        self == .english ? "" : "Always respond in \(englishName). Use simple, natural \(englishName) that a young child would understand."
    }

    static var suggestedDefault: AyaLanguage {
        // Map current device locale to our list, fall back to English.
        let code = Locale.current.language.languageCode?.identifier ?? "en"
        return AyaLanguage(rawValue: code) ?? .english
    }
}

@MainActor
@Observable
final class LocaleService {
    private static let storageKey = "tinyaya.selectedLanguage"

    private(set) var language: AyaLanguage
    private(set) var hasCompletedOnboarding: Bool

    init() {
        let defaults = UserDefaults.standard
        self.hasCompletedOnboarding = defaults.bool(forKey: Self.storageKey + ".done")
        if let raw = defaults.string(forKey: Self.storageKey),
           let lang = AyaLanguage(rawValue: raw) {
            self.language = lang
        } else {
            self.language = AyaLanguage.suggestedDefault
        }
    }

    func complete(with language: AyaLanguage) {
        self.language = language
        self.hasCompletedOnboarding = true
        let defaults = UserDefaults.standard
        defaults.set(language.rawValue, forKey: Self.storageKey)
        defaults.set(true, forKey: Self.storageKey + ".done")
    }

    /// Change language after onboarding. Does not re-show onboarding.
    func setLanguage(_ language: AyaLanguage) {
        self.language = language
        UserDefaults.standard.set(language.rawValue, forKey: Self.storageKey)
    }
}
