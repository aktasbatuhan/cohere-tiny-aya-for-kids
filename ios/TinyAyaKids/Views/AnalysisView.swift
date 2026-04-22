import SwiftUI
import AVFoundation
import UIKit

struct AnalysisView: View {
    @Environment(AppState.self) private var appState
    @State private var draft = ""
    @State private var hasTriggeredAutoLoad = false

    private let starterPrompts = [
        "Tell me a bedtime story about a kind moon.",
        "Why do birds sing?",
        "Can we play a guessing game?",
        "What makes rainbows?",
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                header

                ScrollView {
                    LazyVStack(spacing: 12) {
                        if appState.tinyAyaService.chatMessages.isEmpty {
                            WelcomeCard(isLoaded: appState.tinyAyaService.isModelLoaded)
                        }

                        ForEach(appState.tinyAyaService.chatMessages) { message in
                            ChatBubble(message: message)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 12)
                    .padding(.bottom, 24)
                }

                if !appState.tinyAyaService.microphonePermissionGranted {
                    permissionBanner
                }

                quickPrompts
                composer
            }
            .background(
                LinearGradient(
                    colors: [Color.orange.opacity(0.08), Color.yellow.opacity(0.05), Color(.systemGroupedBackground)],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("Aya")
                        .font(.headline)
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await appState.tinyAyaService.clearConversation() }
                    } label: {
                        Image(systemName: "arrow.counterclockwise")
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
        }
    }

    private var header: some View {
        VStack(spacing: 16) {
            HStack(alignment: .center, spacing: 14) {
                ZStack {
                    Circle()
                        .fill(Color.orange.opacity(0.18))
                        .frame(width: 56, height: 56)

                    Image(systemName: appState.tinyAyaService.isListening ? "waveform.circle.fill" : "face.smiling.fill")
                        .font(.system(size: 28))
                        .foregroundStyle(Color.orange)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("Aya")
                        .font(.title3.weight(.semibold))
                    Text("Offline voice companion")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text(statusLine)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                Spacer()
            }

            if appState.tinyAyaService.isLoading {
                VStack(spacing: 6) {
                    ProgressView(value: appState.tinyAyaService.loadingProgress)
                    Text(appState.tinyAyaService.loadingStatus)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }

            if let error = appState.tinyAyaService.errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            VStack(spacing: 10) {
                Button {
                    Task { await appState.tinyAyaService.toggleVoiceInput() }
                } label: {
                    HStack(spacing: 10) {
                        Image(systemName: appState.tinyAyaService.isListening ? "stop.circle.fill" : "mic.circle.fill")
                            .font(.system(size: 22, weight: .semibold))
                        Text(talkButtonLabel)
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .tint(appState.tinyAyaService.isListening ? .red : .orange)
                .disabled(!appState.tinyAyaService.isModelLoaded || appState.tinyAyaService.isAnalyzing || !appState.tinyAyaService.microphonePermissionGranted)

                if !appState.tinyAyaService.liveTranscript.isEmpty {
                    Text(appState.tinyAyaService.liveTranscript)
                        .font(.subheadline)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .background(Color.orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                }
            }
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .padding(.horizontal, 12)
        .padding(.top, 12)
    }

    private var statusLine: String {
        if appState.tinyAyaService.isLoading {
            return appState.tinyAyaService.loadingStatus
        }
        if !appState.tinyAyaService.isModelLoaded {
            return "Getting ready..."
        }
        return appState.tinyAyaService.voiceStatus
    }

    private var talkButtonLabel: String {
        if appState.tinyAyaService.isListening {
            return "Stop And Send"
        }
        if !appState.tinyAyaService.isModelLoaded {
            return "Aya is getting ready..."
        }
        return "Talk To Aya"
    }

    private var permissionBanner: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "mic.slash.fill")
                .font(.title3)
                .foregroundStyle(.orange)
            VStack(alignment: .leading, spacing: 4) {
                Text("Microphone off")
                    .font(.subheadline.weight(.semibold))
                Text("Aya needs the microphone to hear you. You can still type.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button("Open Settings") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
        }
        .padding(12)
        .background(Color.orange.opacity(0.08))
    }

    private var quickPrompts: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(starterPrompts, id: \.self) { prompt in
                    Button(prompt) {
                        Task { await appState.tinyAyaService.sendMessage(prompt) }
                    }
                    .buttonStyle(.bordered)
                    .disabled(!appState.tinyAyaService.isModelLoaded || appState.tinyAyaService.isAnalyzing)
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 10)
        }
        .background(Color(.secondarySystemGroupedBackground))
    }

    private var composer: some View {
        HStack(alignment: .bottom, spacing: 12) {
            TextField("Type if you don’t want to talk...", text: $draft, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .lineLimit(1...4)

            Button("Send") {
                let message = draft
                draft = ""
                Task { await appState.tinyAyaService.sendMessage(message) }
            }
            .buttonStyle(.borderedProminent)
            .disabled(
                draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                !appState.tinyAyaService.isModelLoaded ||
                appState.tinyAyaService.isAnalyzing
            )
        }
        .padding()
        .background(.thinMaterial)
    }
}

private struct ChatBubble: View {
    let message: TinyAyaService.ChatMessage

    var body: some View {
        HStack {
            if message.role == .assistant {
                content
                Spacer(minLength: 48)
            } else {
                Spacer(minLength: 48)
                content
            }
        }
    }

    private var content: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(message.role == .assistant ? "Aya" : "You")
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(message.content.isEmpty ? "..." : message.content)
                .font(.body)
        }
        .padding(12)
        .background(
            message.role == .assistant ? Color.orange.opacity(0.10) : Color.blue.opacity(0.10),
            in: RoundedRectangle(cornerRadius: 16)
        )
    }
}

private struct WelcomeCard: View {
    let isLoaded: Bool

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "face.smiling.fill")
                .font(.system(size: 44))
                .foregroundStyle(.orange)

            Text("Hi, I'm Aya!")
                .font(.title2.weight(.semibold))

            Text(isLoaded
                ? "Ask me anything, or tap a card below to get started. I live on your phone, so we can chat even without the internet."
                : "I'm getting ready for our first chat. This only takes a moment the first time."
            )
            .font(.subheadline)
            .foregroundStyle(.secondary)
            .multilineTextAlignment(.center)

            HStack(spacing: 8) {
                Image(systemName: "lock.shield.fill")
                    .font(.caption)
                    .foregroundStyle(.green)
                Text("Fully on-device. Nothing leaves your phone.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.top, 4)
        }
        .frame(maxWidth: .infinity)
        .padding(24)
        .background(Color.orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))
    }
}
