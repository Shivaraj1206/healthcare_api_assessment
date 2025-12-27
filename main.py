import requests
import time

API_KEY = "ak_da475e251f58e01d7fdd41edf2dad3e126cce746a4935e09"
BASE_URL = "https://assessment.ksensetech.com/api"

HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

# Fetching all patients (pagination)

def fetch_all_patients():
    all_patients = []
    page = 1
    limit = 5

    while True:
        url = f"{BASE_URL}/patients?page={page}&limit={limit}"
        retries = 0

        while retries < 3:
            try:
                response = requests.get(url, headers=HEADERS, timeout=10)

                if response.status_code == 200:
                    payload = response.json()

                    if "data" not in payload or "pagination" not in payload:
                        retries += 1
                        time.sleep(1)
                        continue

                    all_patients.extend(payload["data"])

                    if payload["pagination"].get("hasNext"):
                        page += 1
                        time.sleep(0.4)
                        break
                    else:
                        return all_patients

                elif response.status_code in [429, 500, 503]:
                    retries += 1
                    time.sleep(1)

                else:
                    return all_patients

            except requests.exceptions.RequestException:
                retries += 1
                time.sleep(1)

        page += 1

    return all_patients



# Safe parsers

def parse_temperature(temp):
    try:
        return float(temp)
    except:
        return None


def parse_bp(bp):
    if not bp or not isinstance(bp, str):
        return None, None
    try:
        s, d = bp.split("/")
        return int(s), int(d)
    except:
        return None, None


def parse_age(age):
    try:
        return int(age)
    except:
        return None



# Fever patients (≥ 99.6°F)

def get_fever_patients(patients):
    fever = []

    for p in patients:
        pid = p.get("patient_id")
        temp = parse_temperature(p.get("temperature"))

        if pid and temp is not None and temp >= 99.6:
            fever.append(pid)

    return fever



# High-risk patients (score ≥ 4)

def get_high_risk_patients(patients):
    high_risk = []

    for p in patients:
        pid = p.get("patient_id")
        age = parse_age(p.get("age"))
        systolic, diastolic = parse_bp(p.get("blood_pressure"))
        temp = parse_temperature(p.get("temperature"))

        if not pid:
            continue

        score = 0

        # Blood pressure score
        if systolic is None or diastolic is None:
            pass
        elif systolic < 120 and diastolic < 80:
            score += 1
        elif 120 <= systolic <= 129 and diastolic < 80:
            score += 2
        elif 130 <= systolic <= 139 or 80 <= diastolic <= 89:
            score += 3
        elif systolic >= 140 or diastolic >= 90:
            score += 4

        # Temperature score
        if temp is None:
            pass
        elif temp <= 99.5:
            score += 0
        elif 99.6 <= temp <= 100.9:
            score += 1
        elif temp >= 101:
            score += 2

        # Age score
        if age is None:
            pass
        elif age < 40:
            score += 1
        elif 40 <= age <= 65:
            score += 1
        elif age > 65:
            score += 2

        if score >= 4:
            high_risk.append(pid)

    return high_risk



# Data quality issues

def get_data_quality_issues(patients):
    issues = set()

    for p in patients:
        pid = p.get("patient_id")
        if not pid:
            continue

        if parse_age(p.get("age")) is None:
            issues.add(pid)

        if parse_temperature(p.get("temperature")) is None:
            issues.add(pid)

        s, d = parse_bp(p.get("blood_pressure"))
        if s is None or d is None:
            issues.add(pid)

    return list(issues)



# Submit results

def submit_results(high_risk, fever, data_quality):
    payload = {
        "high_risk_patients": high_risk,
        "fever_patients": fever,
        "data_quality_issues": data_quality
    }

    response = requests.post(
        f"{BASE_URL}/submit-assessment",
        headers=HEADERS,
        json=payload,
        timeout=10
    )

    print(response.json())



# MAIN

if __name__ == "__main__":
    patients = fetch_all_patients()

    high_risk = get_high_risk_patients(patients)
    fever = get_fever_patients(patients)
    data_quality = get_data_quality_issues(patients)

    submit_results(high_risk, fever, data_quality)
