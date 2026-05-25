"""
Static knowledge base of common symptoms → causes + home remedies.
The LLM is the primary source; this acts as a fast offline fallback / seed.
"""

REMEDY_KB: dict[str, dict] = {
    "headache": {
        "causes": [
            "Tension or stress",
            "Dehydration",
            "Lack of sleep or eye strain",
        ],
        "remedies": [
            "Drink at least 2 glasses of water immediately",
            "Rest in a quiet, dark room for 20–30 minutes",
            "Apply a cold or warm compress to your forehead",
            "Gentle neck and shoulder stretches",
            "Over-the-counter pain relief (e.g. paracetamol) if appropriate",
        ],
    },
    "sore throat": {
        "causes": [
            "Viral infection (cold or flu)",
            "Bacterial infection (e.g. strep throat)",
            "Dry air or allergies",
        ],
        "remedies": [
            "Gargle with warm salt water (½ tsp salt in 8 oz water) 3 times a day",
            "Sip warm honey-lemon tea",
            "Use a humidifier to add moisture to the air",
            "Stay hydrated — warm liquids especially",
            "Suck on throat lozenges to soothe irritation",
        ],
    },
    "fever": {
        "causes": [
            "Viral or bacterial infection",
            "Inflammation",
            "Dehydration",
        ],
        "remedies": [
            "Rest and stay hydrated — drink plenty of fluids",
            "Apply a cool, damp cloth to your forehead",
            "Wear light clothing and keep the room cool",
            "Take paracetamol or ibuprofen as directed on the label",
            "Monitor temperature — seek medical care if above 39.4 °C (103 °F)",
        ],
    },
    "cough": {
        "causes": [
            "Viral upper respiratory infection",
            "Allergies or post-nasal drip",
            "Dry air or irritants",
        ],
        "remedies": [
            "Mix 1 tbsp honey in warm water or herbal tea",
            "Inhale steam for 10 minutes (bowl of hot water + towel over head)",
            "Stay hydrated to thin mucus",
            "Elevate your head with an extra pillow while sleeping",
            "Avoid smoke and other irritants",
        ],
    },
    "stomach pain": {
        "causes": [
            "Indigestion or gas",
            "Gastritis or acid reflux",
            "Food intolerance or mild food poisoning",
        ],
        "remedies": [
            "Drink ginger tea or peppermint tea",
            "Apply a warm heating pad to the abdomen",
            "Eat light, easily digestible foods (BRAT diet: bananas, rice, applesauce, toast)",
            "Avoid spicy, fatty, or acidic foods",
            "Walk gently to help relieve gas",
        ],
    },
    "nausea": {
        "causes": [
            "Motion sickness or inner ear disturbance",
            "Viral gastroenteritis",
            "Eating too fast or overeating",
        ],
        "remedies": [
            "Sip ginger ale or ginger tea slowly",
            "Eat small, bland meals (crackers, dry toast)",
            "Inhale peppermint or lemon essential oil",
            "Rest with your head elevated",
            "Avoid strong odours and greasy foods",
        ],
    },
    "back pain": {
        "causes": [
            "Muscle strain or poor posture",
            "Prolonged sitting or standing",
            "Minor injury or overexertion",
        ],
        "remedies": [
            "Apply ice for 20 min every hour for the first 48 hours, then switch to heat",
            "Gentle stretching: cat-cow pose, child's pose",
            "Take over-the-counter anti-inflammatories (ibuprofen) as directed",
            "Avoid prolonged bed rest — light movement helps",
            "Check and correct your sitting posture",
        ],
    },
    "fatigue": {
        "causes": [
            "Sleep deprivation or poor sleep quality",
            "Dehydration or nutritional deficiency",
            "Stress or anxiety",
        ],
        "remedies": [
            "Aim for 7–9 hours of quality sleep with a consistent schedule",
            "Stay hydrated throughout the day",
            "Eat iron-rich foods (spinach, lentils, lean meat) if diet is poor",
            "Take short 20-minute naps instead of long ones",
            "Light exercise such as a 15-minute walk can boost energy",
        ],
    },
    "cold": {
        "causes": [
            "Rhinovirus or other common cold viruses",
            "Weakened immune system",
            "Exposure to infected individuals",
        ],
        "remedies": [
            "Rest as much as possible",
            "Drink chicken soup or warm broths",
            "Gargle salt water for throat relief",
            "Use saline nasal rinse or spray",
            "Take zinc lozenges within 24 hours of onset",
        ],
    },
}


def find_remedies(symptoms: list[str]) -> dict | None:
    """
    Return the best matching KB entry for the given symptoms.
    Returns None if no match found (LLM will handle it).
    """
    lowered = [s.lower() for s in symptoms]
    for keyword, data in REMEDY_KB.items():
        if any(keyword in sym for sym in lowered):
            return {"matched_on": keyword, **data}
    return None
