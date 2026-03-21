import SwiftUI

struct OnboardingView: View {
    var body: some View {
        ContentUnavailableView(
            "Onboarding Removed",
            systemImage: "sparkles",
            description: Text("The TinyAya MVP opens directly into the chat experience.")
        )
    }
}
