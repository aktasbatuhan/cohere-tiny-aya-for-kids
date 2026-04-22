import SwiftUI
import AVFoundation
import UIKit

// MARK: - Cohere-inspired palette

extension Color {
    static let cohereCoral   = Color(red: 1.00, green: 0.47, blue: 0.35)   // #FF7759
    static let coherePeach   = Color(red: 1.00, green: 0.72, blue: 0.57)   // #FFB791
    static let cohereCream   = Color(red: 1.00, green: 0.96, blue: 0.90)   // #FFF4E6
    static let cohereBlush   = Color(red: 1.00, green: 0.89, blue: 0.85)   // #FFE3D9
    static let coherePlum    = Color(red: 0.20, green: 0.12, blue: 0.20)   // #33203B
    static let coherePlumSoft = Color(red: 0.44, green: 0.30, blue: 0.40)  // #714D67
    static let cohereLavender = Color(red: 0.82, green: 0.56, blue: 0.89)  // #D18EE2
}

struct AnalysisView: View {
    @Environment(AppState.self) private var appState
    @State private var draft = ""
    @State private var hasTriggeredAutoLoad = false
    @State private var mascotBreath = false
    @State private var micPulse = false
    @FocusState private var composerFocused: Bool

    private let starterPrompts: [StarterPrompt] = [
        .init(emoji: "🌙", label: "Bedtime story"),
        .init(emoji: "🎨", label: "Let's draw"),
        .init(emoji: "🌈", label: "Why rainbows?"),
        .init(emoji: "🎵", label: "Sing a song"),
        .init(emoji: "🦖", label: "Dinosaur facts"),
        .init(emoji: "🎲", label: "Play a game"),
    ]

    var body: some View {
        NavigationStack {
            ZStack {
                backgroundGradient.ignoresSafeArea()

                VStack(spacing: 0) {
                    mascotSection

                    if appState.tinyAyaService.chatMessages.isEmpty {
                        Spacer(minLength: 8)
                        privacyPill
                        Spacer()
                    } else {
                        chatScroll
                    }

                    if !appState.tinyAyaService.microphonePermissionGranted {
                        permissionBanner
                            .padding(.horizontal, 16)
                            .padding(.bottom, 8)
                    }

                    if appState.tinyAyaService.chatMessages.isEmpty {
                        promptCards
                            .padding(.bottom, 8)
                    }

                    bottomControls
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        ForEach(AyaLanguage.allCases) { language in
                            Button {
                                appState.localeService.setLanguage(language)
                            } label: {
                                HStack {
                                    Text(language.flag)
                                    Text(language.nativeName)
                                    if appState.localeService.language == language {
                                        Spacer()
                                        Image(systemName: "checkmark")
                                    }
                                }
                            }
                        }
                    } label: {
                        HStack(spacing: 4) {
                            Text(appState.localeService.language.flag)
                                .font(.system(size: 18))
                            Image(systemName: "chevron.down")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundStyle(Color.coherePlumSoft)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(Color.white.opacity(0.75), in: Capsule())
                    }
                    .accessibilityLabel("Change language")
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await appState.tinyAyaService.clearConversation() }
                    } label: {
                        Image(systemName: "arrow.counterclockwise.circle.fill")
                            .font(.system(size: 26))
                            .foregroundStyle(Color.cohereCoral.opacity(0.75))
                    }
                    .disabled(appState.tinyAyaService.chatMessages.isEmpty || appState.tinyAyaService.isAnalyzing)
                    .accessibilityLabel("New conversation")
                }
            }
            .task {
                await appState.tinyAyaService.requestVoicePermissionsIfNeeded()
                if !hasTriggeredAutoLoad && !appState.tinyAyaService.isModelLoaded {
                    hasTriggeredAutoLoad = true
                    await appState.tinyAyaService.loadModel()
                }
            }
            .onAppear {
                withAnimation(.easeInOut(duration: 2.8).repeatForever(autoreverses: true)) {
                    mascotBreath = true
                }
            }
        }
    }

    // MARK: Background

    private var backgroundGradient: some View {
        LinearGradient(
            colors: [Color.cohereCream, Color.cohereBlush, Color.coherePeach.opacity(0.55)],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    // MARK: Mascot

    private var mascotSection: some View {
        VStack(spacing: 14) {
            ZStack {
                // Soft colored glow behind the mascot
                Circle()
                    .fill(Color.cohereCoral.opacity(0.22))
                    .frame(width: 200, height: 200)
                    .blur(radius: 24)

                // Mascot sits on a clean cream circle so the image's white
                // background blends naturally with the art
                Circle()
                    .fill(Color.cohereCream)
                    .frame(width: 168, height: 168)
                    .shadow(color: Color.cohereCoral.opacity(0.20), radius: 18, x: 0, y: 10)
                    .overlay(alignment: .center) {
                        ZStack {
                            Image("AyaMascot")
                                .resizable()
                                .scaledToFit()
                                .frame(width: 158, height: 158)
                                .opacity(mascotStateOpacity)

                            // Overlay state icon for listening/speaking/thinking
                            if appState.tinyAyaService.isListening
                                || appState.tinyAyaService.isSpeaking
                                || appState.tinyAyaService.isAnalyzing {
                                stateOverlay
                            }
                        }
                    }
                    .clipShape(Circle())
                    .scaleEffect(mascotScale)
            }
            .animation(.spring(response: 0.45, dampingFraction: 0.72), value: appState.tinyAyaService.isListening)
            .animation(.spring(response: 0.45, dampingFraction: 0.72), value: appState.tinyAyaService.isSpeaking)

            Text(ayaSubtitle)
                .font(.system(.subheadline, design: .rounded, weight: .medium))
                .foregroundStyle(Color.coherePlumSoft)
                .lineLimit(2)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 36)
                .frame(minHeight: 36)
        }
        .padding(.top, 16)
        .padding(.bottom, 6)
    }

    @ViewBuilder
    private var stateOverlay: some View {
        if appState.tinyAyaService.isListening {
            VStack {
                Spacer()
                HStack(spacing: 6) {
                    Image(systemName: "waveform")
                        .symbolEffect(.variableColor.iterative)
                    Text("listening")
                        .font(.system(.footnote, design: .rounded, weight: .semibold))
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 14)
                .padding(.vertical, 7)
                .background(Color.cohereCoral, in: Capsule())
                .padding(.bottom, 10)
            }
        } else if appState.tinyAyaService.isSpeaking {
            VStack {
                Spacer()
                HStack(spacing: 6) {
                    Image(systemName: "speaker.wave.2.fill")
                    Text("speaking")
                        .font(.system(.footnote, design: .rounded, weight: .semibold))
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 14)
                .padding(.vertical, 7)
                .background(Color.cohereLavender, in: Capsule())
                .padding(.bottom, 10)
            }
        } else if appState.tinyAyaService.isAnalyzing {
            VStack {
                Spacer()
                HStack(spacing: 6) {
                    Image(systemName: "sparkles")
                        .symbolEffect(.pulse)
                    Text("thinking")
                        .font(.system(.footnote, design: .rounded, weight: .semibold))
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 14)
                .padding(.vertical, 7)
                .background(Color.coherePlum, in: Capsule())
                .padding(.bottom, 10)
            }
        }
    }

    private var mascotScale: CGFloat {
        if appState.tinyAyaService.isListening { return 1.06 }
        if appState.tinyAyaService.isSpeaking { return 1.04 }
        return mascotBreath ? 1.025 : 1.0
    }

    private var mascotStateOpacity: Double {
        appState.tinyAyaService.isLoading ? 0.6 : 1.0
    }

    private var ayaSubtitle: String {
        if appState.tinyAyaService.isLoading {
            return appState.tinyAyaService.chatMessages.isEmpty
                ? "Aya is waking up for the first chat..."
                : appState.tinyAyaService.loadingStatus
        }
        if appState.tinyAyaService.isListening { return "Say anything — I'm all ears" }
        if appState.tinyAyaService.isAnalyzing { return "Thinking of something great to say..." }
        if appState.tinyAyaService.isSpeaking { return "" }
        if !appState.tinyAyaService.isModelLoaded { return "Just a moment..." }
        if appState.tinyAyaService.chatMessages.isEmpty {
            return "Tap the big button to talk, or pick a card below"
        }
        return "Tap to keep the chat going"
    }

    // MARK: Privacy pill (empty state)

    private var privacyPill: some View {
        HStack(spacing: 6) {
            Image(systemName: "lock.shield.fill")
                .font(.caption)
                .foregroundStyle(.green)
            Text("Fully on-device. Nothing leaves your phone.")
                .font(.system(.caption, design: .rounded, weight: .medium))
                .foregroundStyle(Color.coherePlumSoft)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(Color.white.opacity(0.7), in: Capsule())
    }

    // MARK: Chat

    private var chatScroll: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 14) {
                    ForEach(appState.tinyAyaService.chatMessages) { message in
                        ChatBubble(message: message)
                            .id(message.id)
                    }
                    if !appState.tinyAyaService.liveTranscript.isEmpty && appState.tinyAyaService.isListening {
                        LiveTranscriptBubble(text: appState.tinyAyaService.liveTranscript)
                    }
                    Color.clear.frame(height: 4).id("bottom")
                }
                .padding(.horizontal, 18)
                .padding(.top, 12)
                .padding(.bottom, 16)
            }
            .onChange(of: appState.tinyAyaService.chatMessages.count) { _, _ in
                withAnimation(.easeOut(duration: 0.25)) {
                    proxy.scrollTo("bottom", anchor: .bottom)
                }
            }
        }
    }

    // MARK: Prompt cards (empty state only)

    private var promptCards: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                ForEach(starterPrompts) { prompt in
                    Button {
                        Task { await appState.tinyAyaService.sendMessage(prompt.sendPayload) }
                    } label: {
                        VStack(spacing: 6) {
                            Text(prompt.emoji)
                                .font(.system(size: 34))
                            Text(prompt.label)
                                .font(.system(.caption, design: .rounded, weight: .semibold))
                                .foregroundStyle(Color.coherePlum)
                        }
                        .frame(width: 96, height: 96)
                        .background(
                            Color.white.opacity(0.85),
                            in: RoundedRectangle(cornerRadius: 22, style: .continuous)
                        )
                        .shadow(color: Color.cohereCoral.opacity(0.18), radius: 8, y: 4)
                    }
                    .buttonStyle(ScaleDownStyle())
                    .disabled(!appState.tinyAyaService.isModelLoaded || appState.tinyAyaService.isAnalyzing)
                    .opacity(!appState.tinyAyaService.isModelLoaded ? 0.5 : 1.0)
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 6)
        }
    }

    // MARK: Bottom (hero mic + text fallback)

    private var bottomControls: some View {
        VStack(spacing: 10) {
            Button {
                Task { await appState.tinyAyaService.toggleVoiceInput() }
            } label: {
                ZStack {
                    if appState.tinyAyaService.isListening {
                        Circle()
                            .stroke(Color.cohereCoral.opacity(0.45), lineWidth: 4)
                            .frame(width: 108, height: 108)
                            .scaleEffect(micPulse ? 1.18 : 1.0)
                            .opacity(micPulse ? 0 : 1)
                    }
                    Circle()
                        .fill(
                            appState.tinyAyaService.isListening
                                ? LinearGradient(
                                    colors: [Color.cohereCoral, Color(red: 0.85, green: 0.25, blue: 0.20)],
                                    startPoint: .top, endPoint: .bottom
                                )
                                : LinearGradient(
                                    colors: [Color.cohereCoral, Color(red: 0.95, green: 0.38, blue: 0.22)],
                                    startPoint: .top, endPoint: .bottom
                                )
                        )
                        .frame(width: 92, height: 92)
                        .shadow(color: Color.cohereCoral.opacity(0.45), radius: 14, y: 8)
                    Image(systemName: appState.tinyAyaService.isListening ? "stop.fill" : "mic.fill")
                        .font(.system(size: 38, weight: .bold))
                        .foregroundStyle(.white)
                }
            }
            .buttonStyle(ScaleDownStyle())
            .disabled(!appState.tinyAyaService.isModelLoaded || appState.tinyAyaService.isAnalyzing || !appState.tinyAyaService.microphonePermissionGranted)
            .accessibilityLabel(appState.tinyAyaService.isListening ? "Stop talking" : "Talk to Aya")
            .onChange(of: appState.tinyAyaService.isListening) { _, listening in
                if listening {
                    withAnimation(.easeOut(duration: 1.2).repeatForever(autoreverses: false)) {
                        micPulse = true
                    }
                } else {
                    micPulse = false
                }
            }

            if let error = appState.tinyAyaService.errorMessage {
                Text(error)
                    .font(.system(.caption, design: .rounded, weight: .medium))
                    .foregroundStyle(.red)
                    .lineLimit(2)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }

            HStack(spacing: 10) {
                TextField("Type if you like", text: $draft)
                    .focused($composerFocused)
                    .font(.system(.body, design: .rounded))
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(Color.white.opacity(0.9), in: Capsule())

                Button {
                    let message = draft
                    draft = ""
                    composerFocused = false
                    Task { await appState.tinyAyaService.sendMessage(message) }
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 36))
                        .foregroundStyle(
                            draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                            !appState.tinyAyaService.isModelLoaded ||
                            appState.tinyAyaService.isAnalyzing
                                ? Color.cohereCoral.opacity(0.35)
                                : Color.cohereCoral
                        )
                }
                .buttonStyle(.plain)
                .disabled(
                    draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                    !appState.tinyAyaService.isModelLoaded ||
                    appState.tinyAyaService.isAnalyzing
                )
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 12)
        }
    }

    // MARK: Permission banner

    private var permissionBanner: some View {
        HStack(alignment: .center, spacing: 10) {
            Image(systemName: "mic.slash.fill")
                .font(.system(size: 20))
                .foregroundStyle(Color.cohereCoral)
            VStack(alignment: .leading, spacing: 2) {
                Text("Microphone is off")
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.coherePlum)
                Text("Aya can still read what you type.")
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(Color.coherePlumSoft)
            }
            Spacer()
            Button("Turn on") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
            .buttonStyle(.borderedProminent)
            .tint(Color.cohereCoral)
            .controlSize(.small)
        }
        .padding(12)
        .background(Color.white.opacity(0.75), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

// MARK: Starter prompts

private struct StarterPrompt: Identifiable {
    let emoji: String
    let label: String
    var id: String { label }
    var sendPayload: String {
        switch label {
        case "Bedtime story":    return "Tell me a cozy bedtime story about a kind moon."
        case "Let's draw":       return "Can we imagine drawing a silly animal together?"
        case "Why rainbows?":    return "Why do rainbows have so many colors?"
        case "Sing a song":      return "Can you sing a little song about friendship?"
        case "Dinosaur facts":   return "Tell me the coolest dinosaur fact you know."
        case "Play a game":      return "Let's play a guessing game together."
        default:                  return label
        }
    }
}

// MARK: Chat bubbles

private struct ChatBubble: View {
    let message: TinyAyaService.ChatMessage

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            if message.role == .assistant {
                avatarCircle
                bubble
                Spacer(minLength: 30)
            } else {
                Spacer(minLength: 30)
                bubble
            }
        }
    }

    private var avatarCircle: some View {
        ZStack {
            Circle()
                .fill(Color.cohereCream)
                .frame(width: 34, height: 34)
                .shadow(color: Color.cohereCoral.opacity(0.15), radius: 3, y: 1)
            Image("AyaMascot")
                .resizable()
                .scaledToFit()
                .frame(width: 32, height: 32)
                .clipShape(Circle())
        }
    }

    private var bubble: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(message.content.isEmpty ? "…" : message.content)
                .font(.system(.body, design: .rounded))
                .foregroundStyle(message.role == .assistant
                                 ? Color.coherePlum
                                 : .white)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(
            message.role == .assistant
                ? AnyShapeStyle(Color.white.opacity(0.95))
                : AnyShapeStyle(LinearGradient(
                    colors: [Color.cohereCoral, Color(red: 0.95, green: 0.38, blue: 0.22)],
                    startPoint: .topLeading, endPoint: .bottomTrailing)),
            in: bubbleShape(isAssistant: message.role == .assistant)
        )
        .shadow(color: .black.opacity(0.06), radius: 4, y: 2)
    }

    private func bubbleShape(isAssistant: Bool) -> UnevenRoundedRectangle {
        UnevenRoundedRectangle(
            cornerRadii: .init(
                topLeading: 18,
                bottomLeading: isAssistant ? 6 : 18,
                bottomTrailing: isAssistant ? 18 : 6,
                topTrailing: 18
            ),
            style: .continuous
        )
    }
}

private struct LiveTranscriptBubble: View {
    let text: String
    var body: some View {
        HStack {
            Spacer(minLength: 30)
            Text(text)
                .font(.system(.body, design: .rounded))
                .foregroundStyle(Color.coherePlum)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(
                    Color.cohereCoral.opacity(0.18),
                    in: RoundedRectangle(cornerRadius: 18, style: .continuous)
                )
        }
    }
}

// MARK: Button style

private struct ScaleDownStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.92 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.6), value: configuration.isPressed)
    }
}
