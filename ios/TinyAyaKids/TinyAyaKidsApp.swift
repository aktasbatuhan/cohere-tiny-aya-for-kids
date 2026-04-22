import SwiftUI

@main
struct TinyAyaKidsApp: App {
    @State private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(appState)
        }
    }
}

@MainActor
@Observable
final class AppState {
    let localeService: LocaleService
    let tinyAyaService: TinyAyaService

    init() {
        let locale = LocaleService()
        self.localeService = locale
        self.tinyAyaService = TinyAyaService(locale: locale)
    }
}

struct RootView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        if appState.localeService.hasCompletedOnboarding {
            ContentView()
        } else {
            OnboardingView()
        }
    }
}
