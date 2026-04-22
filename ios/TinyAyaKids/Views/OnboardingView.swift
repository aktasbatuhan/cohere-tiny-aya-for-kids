import SwiftUI

struct OnboardingView: View {
    @Environment(AppState.self) private var appState
    @State private var selectedLanguage: AyaLanguage

    init() {
        _selectedLanguage = State(initialValue: AyaLanguage.suggestedDefault)
    }

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color.cohereCream, Color.cohereBlush, Color.coherePeach.opacity(0.55)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 18) {
                Spacer(minLength: 12)

                // Mascot
                ZStack {
                    Circle()
                        .fill(Color.cohereCoral.opacity(0.20))
                        .frame(width: 180, height: 180)
                        .blur(radius: 22)
                    Circle()
                        .fill(Color.cohereCream)
                        .frame(width: 148, height: 148)
                        .shadow(color: Color.cohereCoral.opacity(0.20), radius: 14, y: 8)
                        .overlay(
                            Image("AyaMascot")
                                .resizable()
                                .scaledToFit()
                                .frame(width: 140, height: 140)
                        )
                        .clipShape(Circle())
                }

                VStack(spacing: 6) {
                    Text("Hi, I'm Aya!")
                        .font(.system(.largeTitle, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.coherePlum)
                    Text("Which language should we chat in?")
                        .font(.system(.body, design: .rounded))
                        .foregroundStyle(Color.coherePlumSoft)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 32)
                }

                // Language grid
                ScrollView {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 140, maximum: 200), spacing: 10)], spacing: 10) {
                        ForEach(AyaLanguage.allCases) { language in
                            LanguageChip(
                                language: language,
                                isSelected: selectedLanguage == language
                            ) {
                                selectedLanguage = language
                            }
                        }
                    }
                    .padding(.horizontal, 18)
                    .padding(.vertical, 10)
                }
                .frame(maxHeight: 380)

                VStack(spacing: 10) {
                    Button {
                        appState.localeService.complete(with: selectedLanguage)
                    } label: {
                        HStack(spacing: 8) {
                            Text("Start chatting in \(selectedLanguage.nativeName)")
                                .font(.system(.headline, design: .rounded, weight: .semibold))
                            Image(systemName: "arrow.right.circle.fill")
                                .font(.system(size: 20))
                        }
                        .foregroundStyle(.white)
                        .padding(.horizontal, 22)
                        .padding(.vertical, 14)
                        .frame(maxWidth: .infinity)
                        .background(
                            LinearGradient(
                                colors: [Color.cohereCoral, Color(red: 0.95, green: 0.38, blue: 0.22)],
                                startPoint: .top, endPoint: .bottom
                            ),
                            in: Capsule()
                        )
                        .shadow(color: Color.cohereCoral.opacity(0.40), radius: 10, y: 6)
                    }
                    .buttonStyle(ScaleDownStyle())

                    HStack(spacing: 6) {
                        Image(systemName: "lock.shield.fill")
                            .font(.caption)
                            .foregroundStyle(.green)
                        Text("Fully on-device. Nothing leaves your phone.")
                            .font(.system(.caption, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.coherePlumSoft)
                    }
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 20)
            }
        }
    }
}

private struct LanguageChip: View {
    let language: AyaLanguage
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Text(language.flag)
                    .font(.system(size: 22))
                VStack(alignment: .leading, spacing: 0) {
                    Text(language.nativeName)
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.coherePlum)
                        .lineLimit(1)
                }
                Spacer(minLength: 0)
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(Color.cohereCoral)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(
                isSelected ? Color.white : Color.white.opacity(0.6),
                in: RoundedRectangle(cornerRadius: 14, style: .continuous)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(isSelected ? Color.cohereCoral : Color.clear, lineWidth: 2)
            )
            .shadow(color: Color.cohereCoral.opacity(isSelected ? 0.25 : 0.0), radius: 6, y: 3)
        }
        .buttonStyle(.plain)
    }
}

private struct ScaleDownStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.96 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: configuration.isPressed)
    }
}
