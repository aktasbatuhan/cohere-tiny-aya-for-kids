import SwiftUI

struct HealthView: View {
    var body: some View {
        ContentUnavailableView(
            "Health View Removed",
            systemImage: "heart.text.square",
            description: Text("HealthKit from the copied medical project is not part of the TinyAya MVP.")
        )
    }
}
