import Foundation
import HealthKit
import SwiftUI

@MainActor
@Observable
class HealthKitManager {
    // MARK: - Published State
    var isAuthorized = false
    var isLoading = false
    var errorMessage: String?

    // MARK: - Health Metrics
    var heartRate: Double?
    var heartRateVariability: Double?
    var bloodPressureSystolic: Double?
    var bloodPressureDiastolic: Double?
    var oxygenSaturation: Double?
    var respiratoryRate: Double?
    var bodyTemperature: Double?
    var stepCount: Double?
    var activeEnergy: Double?
    var restingEnergy: Double?
    var weight: Double?
    var height: Double?
    var bmi: Double?
    var sleepHours: Double?

    var lastUpdated: Date?

    // MARK: - Health Store
    private let healthStore = HKHealthStore()

    // MARK: - Data Types
    private let readTypes: Set<HKObjectType> = {
        var types: Set<HKObjectType> = []

        // Vital Signs
        if let heartRate = HKQuantityType.quantityType(forIdentifier: .heartRate) {
            types.insert(heartRate)
        }
        if let hrv = HKQuantityType.quantityType(forIdentifier: .heartRateVariabilitySDNN) {
            types.insert(hrv)
        }
        if let systolic = HKQuantityType.quantityType(forIdentifier: .bloodPressureSystolic) {
            types.insert(systolic)
        }
        if let diastolic = HKQuantityType.quantityType(forIdentifier: .bloodPressureDiastolic) {
            types.insert(diastolic)
        }
        if let o2 = HKQuantityType.quantityType(forIdentifier: .oxygenSaturation) {
            types.insert(o2)
        }
        if let respRate = HKQuantityType.quantityType(forIdentifier: .respiratoryRate) {
            types.insert(respRate)
        }
        if let temp = HKQuantityType.quantityType(forIdentifier: .bodyTemperature) {
            types.insert(temp)
        }

        // Activity
        if let steps = HKQuantityType.quantityType(forIdentifier: .stepCount) {
            types.insert(steps)
        }
        if let active = HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned) {
            types.insert(active)
        }
        if let resting = HKQuantityType.quantityType(forIdentifier: .basalEnergyBurned) {
            types.insert(resting)
        }

        // Body Measurements
        if let weight = HKQuantityType.quantityType(forIdentifier: .bodyMass) {
            types.insert(weight)
        }
        if let height = HKQuantityType.quantityType(forIdentifier: .height) {
            types.insert(height)
        }
        if let bmi = HKQuantityType.quantityType(forIdentifier: .bodyMassIndex) {
            types.insert(bmi)
        }

        // Sleep
        if let sleep = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis) {
            types.insert(sleep)
        }

        // ECG (if available)
        types.insert(HKObjectType.electrocardiogramType())

        return types
    }()

    // MARK: - Initialization
    init() {
        checkAuthorizationStatus()
    }

    // MARK: - Authorization
    private func checkAuthorizationStatus() {
        guard HKHealthStore.isHealthDataAvailable() else {
            errorMessage = "HealthKit is not available on this device"
            return
        }

        // Check if we have any authorization
        if let heartRateType = HKQuantityType.quantityType(forIdentifier: .heartRate) {
            let status = healthStore.authorizationStatus(for: heartRateType)
            isAuthorized = status == .sharingAuthorized
        }
    }

    func requestAuthorization() async {
        guard HKHealthStore.isHealthDataAvailable() else {
            errorMessage = "HealthKit is not available on this device"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            try await healthStore.requestAuthorization(toShare: [], read: readTypes)
            isAuthorized = true
            await fetchAllHealthData()
        } catch {
            errorMessage = "Authorization failed: \(error.localizedDescription)"
            isAuthorized = false
        }

        isLoading = false
    }

    // MARK: - Data Fetching
    func fetchAllHealthData() async {
        guard isAuthorized else { return }

        isLoading = true

        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.fetchHeartRate() }
            group.addTask { await self.fetchHeartRateVariability() }
            group.addTask { await self.fetchBloodPressure() }
            group.addTask { await self.fetchOxygenSaturation() }
            group.addTask { await self.fetchRespiratoryRate() }
            group.addTask { await self.fetchStepCount() }
            group.addTask { await self.fetchActiveEnergy() }
            group.addTask { await self.fetchWeight() }
            group.addTask { await self.fetchHeight() }
            group.addTask { await self.fetchSleepData() }
        }

        calculateBMI()
        lastUpdated = Date()
        isLoading = false
    }

    private func fetchHeartRate() async {
        guard let type = HKQuantityType.quantityType(forIdentifier: .heartRate) else { return }

        if let sample = await fetchMostRecentSample(for: type) {
            let unit = HKUnit.count().unitDivided(by: .minute())
            heartRate = sample.quantity.doubleValue(for: unit)
        }
    }

    private func fetchHeartRateVariability() async {
        guard let type = HKQuantityType.quantityType(forIdentifier: .heartRateVariabilitySDNN) else { return }

        if let sample = await fetchMostRecentSample(for: type) {
            heartRateVariability = sample.quantity.doubleValue(for: .secondUnit(with: .milli))
        }
    }

    private func fetchBloodPressure() async {
        if let systolicType = HKQuantityType.quantityType(forIdentifier: .bloodPressureSystolic),
           let sample = await fetchMostRecentSample(for: systolicType) {
            bloodPressureSystolic = sample.quantity.doubleValue(for: .millimeterOfMercury())
        }

        if let diastolicType = HKQuantityType.quantityType(forIdentifier: .bloodPressureDiastolic),
           let sample = await fetchMostRecentSample(for: diastolicType) {
            bloodPressureDiastolic = sample.quantity.doubleValue(for: .millimeterOfMercury())
        }
    }

    private func fetchOxygenSaturation() async {
        guard let type = HKQuantityType.quantityType(forIdentifier: .oxygenSaturation) else { return }

        if let sample = await fetchMostRecentSample(for: type) {
            oxygenSaturation = sample.quantity.doubleValue(for: .percent()) * 100
        }
    }

    private func fetchRespiratoryRate() async {
        guard let type = HKQuantityType.quantityType(forIdentifier: .respiratoryRate) else { return }

        if let sample = await fetchMostRecentSample(for: type) {
            respiratoryRate = sample.quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute()))
        }
    }

    private func fetchStepCount() async {
        guard let type = HKQuantityType.quantityType(forIdentifier: .stepCount) else { return }

        let calendar = Calendar.current
        let startOfDay = calendar.startOfDay(for: Date())

        stepCount = await fetchSumSample(for: type, from: startOfDay)
    }

    private func fetchActiveEnergy() async {
        guard let type = HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned) else { return }

        let calendar = Calendar.current
        let startOfDay = calendar.startOfDay(for: Date())

        activeEnergy = await fetchSumSample(for: type, from: startOfDay, unit: .kilocalorie())
    }

    private func fetchWeight() async {
        guard let type = HKQuantityType.quantityType(forIdentifier: .bodyMass) else { return }

        if let sample = await fetchMostRecentSample(for: type) {
            weight = sample.quantity.doubleValue(for: .gramUnit(with: .kilo))
        }
    }

    private func fetchHeight() async {
        guard let type = HKQuantityType.quantityType(forIdentifier: .height) else { return }

        if let sample = await fetchMostRecentSample(for: type) {
            height = sample.quantity.doubleValue(for: .meterUnit(with: .centi))
        }
    }

    private func fetchSleepData() async {
        guard let type = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis) else { return }

        let calendar = Calendar.current
        let endDate = Date()
        let startDate = calendar.date(byAdding: .day, value: -1, to: endDate)!

        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: endDate, options: .strictStartDate)

        await withCheckedContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: type,
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: nil
            ) { [weak self] _, samples, error in
                Task { @MainActor in
                    guard let samples = samples as? [HKCategorySample] else {
                        continuation.resume()
                        return
                    }

                    var totalSleep: TimeInterval = 0
                    for sample in samples {
                        if sample.value == HKCategoryValueSleepAnalysis.asleepUnspecified.rawValue ||
                           sample.value == HKCategoryValueSleepAnalysis.asleepCore.rawValue ||
                           sample.value == HKCategoryValueSleepAnalysis.asleepDeep.rawValue ||
                           sample.value == HKCategoryValueSleepAnalysis.asleepREM.rawValue {
                            totalSleep += sample.endDate.timeIntervalSince(sample.startDate)
                        }
                    }

                    self?.sleepHours = totalSleep / 3600
                    continuation.resume()
                }
            }

            healthStore.execute(query)
        }
    }

    private func calculateBMI() {
        guard let w = weight, let h = height, h > 0 else { return }
        let heightInMeters = h / 100
        bmi = w / (heightInMeters * heightInMeters)
    }

    // MARK: - Helper Methods
    private func fetchMostRecentSample(for type: HKQuantityType) async -> HKQuantitySample? {
        let predicate = HKQuery.predicateForSamples(
            withStart: Calendar.current.date(byAdding: .day, value: -7, to: Date()),
            end: Date(),
            options: .strictStartDate
        )

        let sortDescriptor = NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)

        return await withCheckedContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: type,
                predicate: predicate,
                limit: 1,
                sortDescriptors: [sortDescriptor]
            ) { _, samples, error in
                continuation.resume(returning: samples?.first as? HKQuantitySample)
            }

            healthStore.execute(query)
        }
    }

    private func fetchSumSample(for type: HKQuantityType, from startDate: Date, unit: HKUnit = .count()) async -> Double? {
        let predicate = HKQuery.predicateForSamples(
            withStart: startDate,
            end: Date(),
            options: .strictStartDate
        )

        return await withCheckedContinuation { continuation in
            let query = HKStatisticsQuery(
                quantityType: type,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum
            ) { _, result, error in
                let value = result?.sumQuantity()?.doubleValue(for: unit)
                continuation.resume(returning: value)
            }

            healthStore.execute(query)
        }
    }

    // MARK: - Health Insights
    func generateHealthInsights(for analysisResult: AnalysisResult) -> [HealthInsight] {
        var insights: [HealthInsight] = []

        // Heart rate insights
        if let hr = heartRate {
            if hr > 100 {
                insights.append(HealthInsight(
                    category: "Cardiovascular",
                    title: "Elevated Heart Rate",
                    description: "Your resting heart rate of \(Int(hr)) bpm is elevated. Consider correlation with imaging findings.",
                    severity: .moderate,
                    metric: "Heart Rate: \(Int(hr)) bpm"
                ))
            } else if hr < 50 {
                insights.append(HealthInsight(
                    category: "Cardiovascular",
                    title: "Low Heart Rate",
                    description: "Your heart rate of \(Int(hr)) bpm is below normal resting range.",
                    severity: .mild,
                    metric: "Heart Rate: \(Int(hr)) bpm"
                ))
            }
        }

        // Blood pressure insights
        if let sys = bloodPressureSystolic, let dia = bloodPressureDiastolic {
            if sys > 140 || dia > 90 {
                insights.append(HealthInsight(
                    category: "Cardiovascular",
                    title: "Elevated Blood Pressure",
                    description: "Blood pressure \(Int(sys))/\(Int(dia)) mmHg indicates hypertension. Consider cardiac imaging correlation.",
                    severity: .moderate,
                    metric: "BP: \(Int(sys))/\(Int(dia)) mmHg"
                ))
            }
        }

        // Oxygen saturation
        if let o2 = oxygenSaturation, o2 < 95 {
            insights.append(HealthInsight(
                category: "Respiratory",
                title: "Low Oxygen Saturation",
                description: "SpO2 of \(Int(o2))% is below normal. Correlate with pulmonary imaging findings.",
                severity: o2 < 90 ? .severe : .moderate,
                metric: "SpO2: \(Int(o2))%"
            ))
        }

        // Activity insights
        if let steps = stepCount, steps < 3000 {
            insights.append(HealthInsight(
                category: "Activity",
                title: "Low Activity Level",
                description: "Daily step count of \(Int(steps)) is below recommended levels.",
                severity: .mild,
                metric: "Steps: \(Int(steps))"
            ))
        }

        return insights
    }
}

struct HealthInsight: Identifiable {
    let id = UUID()
    let category: String
    let title: String
    let description: String
    let severity: MedicalFinding.Severity
    let metric: String
}