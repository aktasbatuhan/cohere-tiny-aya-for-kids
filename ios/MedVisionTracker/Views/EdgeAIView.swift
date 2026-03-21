import SwiftUI

struct EdgeAIView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    VStack(spacing: 12) {
                        ZStack {
                            Circle()
                                .fill(.blue.opacity(0.12))
                                .frame(width: 96, height: 96)

                            Image(systemName: "iphone.gen3.radiowaves.left.and.right")
                                .font(.system(size: 42))
                                .foregroundStyle(.blue)
                        }

                        Text("Offline TinyAya")
                            .font(.title2)
                            .fontWeight(.bold)

                        Text("This MVP is testing whether a small multilingual model can chat safely with children on-device, starting with iPhone.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))

                    infoCard(
                        title: "Current stack",
                        rows: [
                            ("Runtime", appState.medGemmaService.selectedRuntime.displayName),
                            ("Model", appState.medGemmaService.activeModelDisplayName),
                            ("Priority", "iOS first"),
                            ("Cross-platform", "llama.cpp is the current TinyAya path"),
                        ]
                    )

                    infoCard(
                        title: "Device status",
                        rows: [
                            ("Device RAM", String(format: "%.1f GB", appState.medGemmaService.deviceMemoryGB)),
                            ("MLX memory limit", "\(appState.medGemmaService.mlxMemoryLimitMB) MB"),
                            ("Loaded", appState.medGemmaService.isModelLoaded ? "Yes" : "No"),
                            ("Current memory", "\(Int(appState.medGemmaService.memoryUsageMB)) MB"),
                        ]
                    )

                    VStack(alignment: .leading, spacing: 10) {
                        Text("Why on-device first")
                            .font(.headline)

                        bullet("No child conversation leaves the device.")
                        bullet("We can measure real iPhone latency before over-engineering Android support.")
                        bullet("The same benchmark repo can later be used to compare TinyAya against portable runtimes.")
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
                }
                .padding()
            }
            .navigationTitle("Edge AI")
        }
    }

    private func infoCard(title: String, rows: [(String, String)]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.headline)

            ForEach(rows, id: \.0) { row in
                HStack {
                    Text(row.0)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(row.1)
                        .fontWeight(.medium)
                }
                .font(.subheadline)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    private func bullet(_ text: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
                .font(.caption)
            Text(text)
                .font(.subheadline)
        }
    }
}
