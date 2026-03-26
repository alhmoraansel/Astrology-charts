# dasha_results.py
# Comprehensive Classical Results for Vedic Dashas
# Extracted from Parashara's classical texts (Ch 46-63)

# ==============================================================================
# SECTION 1: MAHADASHA GENERAL EFFECTS (Main Periods)
# ==============================================================================
MAHADASHAS = {
    "Sun": {
        "favorable": "Wealth, high government honors (like Army Chief), elephants, conveyances, clothes, agricultural products, and birth of a son.",
        "unfavorable": "Loss of wealth, government punishment, defamation, father's distress, uncles' distress, and unprovoked anxiety."
    },
    "Moon": {
        "favorable": "Opulence, glory, dawn of fortune, government positions, birth of children, acquisition of cattle, and extraordinary luxuries.",
        "unfavorable": "Idiocy, mental tension, trouble from employees and mother, government enmity, and loss of wealth."
    },
    "Mars": {
        "favorable": "Kingdom acquisition, high political positions, foreign wealth, ornaments, good relations with siblings, and victory over enemies through valor.",
        "unfavorable": "Loss of wealth, deep distress, and misfortune."
    },
    "Rahu": {
        "favorable": "Wealth, agriculture, new house construction, religious inclination, foreign government recognition, and clothes. (Especially in Taurus/Gemini/Virgo, Angular/Trine houses).",
        "unfavorable": "Loss of position, destroyed house, bad food, wife/children trouble, and mental agony."
    },
    "Jupiter": {
        "favorable": "Devotion to deities/Brahmins, successful religious sacrifices, kingdom acquisition, high felicity, conveyances, and wife/children happiness.",
        "unfavorable": "Loss of house, distress to children, loss of cattle, and forced pilgrimage."
    },
    "Saturn": {
        "favorable": "Glory, educational success, government favors, Army Commander position, property, and the benevolence of Goddess Lakshmi.",
        "unfavorable": "Ill effects from poison, weapon injuries, separation from father, imprisonment, and government displeasure."
    },
    "Mercury": {
        "favorable": "Sweetish preparations, business profits, knowledge improvement, government benevolence, and physical health.",
        "unfavorable": "Rheumatism, jaundice, urinary troubles, dependence on others, theft, and foreign exile."
    },
    "Ketu": {
        "favorable": "Headship of a village/country, elephants, Raj Yog (royal combinations), and foreign gains.",
        "unfavorable": "Imprisonment, menial company, destruction of kinsmen, and disease."
    },
    "Venus": {
        "favorable": "Fancy clothes, ornaments, sweet preparations daily, luxurious song and dance functions, recovery of lost wealth, and birth of grandchildren.",
        "unfavorable": "Defamation, cattle destruction, wife distress, and business losses. (Remedy: Shatarudriya/Mrityunjaya Japa and donating a cow/buffalo)."
    }
}

# ==============================================================================
# SECTION 2: HOUSE LORD EFFECTS
# ==============================================================================
HOUSE_LORD_EFFECTS = {
    1: "Physical well-being.",
    2: "Distress, possibility of death, or death-like sufferings (Maraka).",
    3: "Unfavorable effects and obstacles.",
    4: "Acquisition of house and land.",
    5: "Educational progress and happiness from children.",
    6: "Danger from enemies and ill health.",
    7: "Distress, possibility of death, or death-like sufferings (Maraka).",
    8: "Possibility of death and financial ruin.",
    9: "Unexpected wealth, religious-mindedness, educational improvement.",
    10: "Government awards and recognition.",
    11: "Obstacles in wealth and possibility of disease.",
    12: "Distress and danger from diseases."
}

# ==============================================================================
# SECTION 3: ANTARDASHA EFFECTS (Sub-Periods)
# ==============================================================================
# Format: ANTARDASHAS[Main_Mahadasha][Sub_Antardasha]
ANTARDASHAS = {
    "Sun": {
        "Sun": {"effects": "Wealth, grains.", "unfavorable": "Premature death if 2nd/7th lord.", "remedy": "Mrityunjaya Japa / Sun worship."},
        "Moon": {"effects": "Marriage, son's birth, house, cattle, king's favor.", "unfavorable": "Wife/children distress, jail, urinary troubles.", "remedy": "White cow charity."},
        "Mars": {"effects": "Land, army commander position, destruction of enemies.", "unfavorable": "Brutality, mental ailment, jail, brother disputes.", "remedy": "Vedas recitation, Vrashotsarg."},
        "Rahu": {"effects": "First 2 months: Thieves, snake danger. Later: Fame, son's birth, king's favor.", "unfavorable": "Dysentery, skin enlargement.", "remedy": "Durga worship, black cow."},
        "Jupiter": {"effects": "Palanquin comforts, kingdom, religious oblations.", "unfavorable": "Sinful deeds, king's displeasure, body pains.", "remedy": "Kapila cow (tawny), gold charity."},
        "Saturn": {"effects": "Foes destroyed, wealth from many sources, fame.", "unfavorable": "Rheumatism, rigorous jail, claimant disputes.", "remedy": "Black cow, goat charity."},
        "Mercury": {"effects": "Indra-like happiness, sweet drinks, pearls, assumed names.", "unfavorable": "Jaundice, body distress, foreign exile.", "remedy": "Vishnu Sahasranam, silver idol."},
        "Ketu": {"effects": "Satisfaction, clothes.", "unfavorable": "Tooth/cheek diseases, lost position, father's death.", "remedy": "Shat Chandi Path, goat charity."},
        "Venus": {"effects": "Pearls, musical instruments, sweet food daily, cattle.", "unfavorable": "Dysentery, fevers, wife distress.", "remedy": "Rudra Japa, tawny cow."}
    },
    "Moon": {
        "Moon": {"effects": "Horses, elephants, divine devotion, kingship.", "unfavorable": "Lethargy, mother's distress, jail, body pains.", "remedy": "Tawny cow charity."},
        "Mars": {"effects": "Ornaments, agriculture increase, fortune.", "unfavorable": "Employee antagonism, home losses, hot temperament.", "remedy": "None specified."},
        "Rahu": {"effects": "Gains from South-West, holy pilgrimages.", "unfavorable": "Scorpions, snakes, loss of reputation.", "remedy": "Rahu Japa, goat."},
        "Jupiter": {"effects": "Isht Devata beneficence, kingdom, marriage.", "unfavorable": "Preceptor/father's death, unpalatable food.", "remedy": "Shiva Sahasranam, gold."},
        "Saturn": {"effects": "Sudra assistance, agricultural profits, son's birth.", "unfavorable": "Holy river bathing (due to distress), enemy troubles.", "remedy": "Mrityunjaya, black cow."},
        "Mercury": {"effects": "Soma Rasa (tasty syrups), pearls, Shastra discussions.", "unfavorable": "Jail, agriculture loss, fever fears.", "remedy": "Vishnu Sahasranam, goat."},
        "Ketu": {"effects": "Wealth, religious inclination.", "unfavorable": "Enemy interference, body afflictions.", "remedy": "Mrityunjaya Japa."},
        "Venus": {"effects": "Sweet preparations daily, beautiful women, underground hidden treasure.", "unfavorable": "Deportation, snake/thief danger.", "remedy": "Rudra Japa, white cow, silver."},
        "Sun": {"effects": "Kingdom recovery, village acquisition, friend assistance.", "unfavorable": "Snake/poison danger, fever, foreign travel troubles.", "remedy": "Shiva worship."}
    },
    "Mars": {
        "Mars": {"effects": "Lakshmi's beneficence, kingdom recovery, buffalo/cow gains.", "unfavorable": "Urinary troubles, wounds, snake danger.", "remedy": "Rudra Japa, red bull."},
        "Rahu": {"effects": "Ganges bathing, foreign journeys.", "unfavorable": "Wind/bile disease, snake danger, goblins.", "remedy": "Naga Puja, Mrityunjaya."},
        "Jupiter": {"effects": "Good health, reputation, property.", "unfavorable": "Goblins (Pret), bilious diseases, servant loss.", "remedy": "Shiva Sahasranam."},
        "Saturn": {"effects": "Grandchildren, cow increase.", "unfavorable": "Yavana kings danger, war defeat, urinary troubles.", "remedy": "None specified."},
        "Mercury": {"effects": "Pious persons association, sweetish preparations, commander role.", "unfavorable": "Heart disease, harsh speech, dacoits during travel.", "remedy": "Vishnu Sahasranam, horse charity."},
        "Ketu": {"effects": "Commander position, employer wealth, oblations.", "unfavorable": "Tooth trouble, tiger/thief distress, leprosy.", "remedy": "None specified."},
        "Venus": {"effects": "Elephants, horses, perfumery, wells/reservoirs construction.", "unfavorable": "Family dissensions, cattle destruction.", "remedy": "Cow/buffalo charity."},
        "Sun": {"effects": "Potency, business profits, king audience.", "unfavorable": "Forehead troubles, fever, dysentery.", "remedy": "Surya worship."},
        "Moon": {"effects": "Perfumes, marriage, parents' good relations.", "unfavorable": "War danger, death, mental agony.", "remedy": "Durga/Lakshmi Mantras."}
    },
    "Rahu": {
        "Rahu": {"effects": "Kingdom, enthusiasm, cordial king relations.", "unfavorable": "Wounds, official antagonism, disease.", "remedy": "Rahu worship/charity."},
        "Jupiter": {"effects": "Candr-like wealth growth, South-East journeys, good food.", "unfavorable": "Heart disease, defamation.", "remedy": "Shiva/gold."},
        "Saturn": {"effects": "Garden construction, Sudra wealth, sudden ornament gains.", "unfavorable": "Menial danger, Gulma affliction, unpalatable food.", "remedy": "Black cow/she-buffalo."},
        "Mercury": {"effects": "Wednesday Raj Yog, bed/women comforts, Purana discourses.", "unfavorable": "Speaking lies, snake/thief fears.", "remedy": "Vishnu Sahasranam."},
        "Ketu": {"effects": "Rheumatic fever, foreign journeys, gold acquisition.", "unfavorable": "Wounds, parental separation, body distress.", "remedy": "Goat charity."},
        "Venus": {"effects": "Sacred thread ceremony, sweet food, house construction.", "unfavorable": "Employer death danger, stomach pain, diabetes.", "remedy": "Durga/Lakshmi worship."},
        "Sun": {"effects": "Village headship, foreign recognition, elephants.", "unfavorable": "Fevers, dysentery, travels.", "remedy": "Surya worship."},
        "Moon": {"effects": "Property increase, deity worship.", "unfavorable": "Evil spirits, wild animals, stomach disorders.", "remedy": "White cow/female buffalo."},
        "Mars": {"effects": "Red garments, commander role.", "unfavorable": "Wife/child antagonism, wounds, lethargy.", "remedy": "Cow/bull charity."}
    },
    "Jupiter": {
        "Jupiter": {"effects": "Sovereignty, blue-colored horse gains, Westward journeys.", "unfavorable": "Menial association, coparcener slander.", "remedy": "Rudr/Shiva Sahasranam."},
        "Saturn": {"effects": "Enemy property acquisition.", "unfavorable": "Fever, wound infliction, employment loss.", "remedy": "Vishnu Sahasranam, black cow."},
        "Mercury": {"effects": "Conveyances.", "unfavorable": "Fever, dysentery, foreign wanderings.", "remedy": "Vishnu Sahasranam."},
        "Ketu": {"effects": "Palanquin, Muslim king (Yavana) wealth.", "unfavorable": "Coarse food, death ceremonies food, king's wrath.", "remedy": "Mrityunjaya."},
        "Venus": {"effects": "Blue/red articles, Eastward extraordinary income, music society.", "unfavorable": "Father-in-law disputes, snake/king wrath.", "remedy": "Tawny cow/buffalo."},
        "Sun": {"effects": "Glory, children increase.", "unfavorable": "Nervous disorder, sins, reluctance to good deeds.", "remedy": "Adhitya Hridaya Path."},
        "Moon": {"effects": "Good food, grandchildren, religious inclinations.", "unfavorable": "Maternal uncle separation, coparcener quarrels.", "remedy": "Durga Saptashati."},
        "Mars": {"effects": "Marriage, strength/valor, sweetish preparations.", "unfavorable": "Eye trouble, house loss.", "remedy": "Bull charity."},
        "Rahu": {"effects": "Village sovereignty, holy bathing.", "unfavorable": "Goblins, bad dreams, snakes.", "remedy": "Mrityunjaya, goat."}
    },
    "Saturn": {
        "Saturn": {"effects": "Commander role, elephants.", "unfavorable": "Bleeding gums, dysentery, weapon injuries.", "remedy": "Mrityunjaya."},
        "Mercury": {"effects": "Yagyas, Puranas listening, sweet preparations.", "unfavorable": "Business failures, anxiety.", "remedy": "Vishnu Sahasranam, grains."},
        "Ketu": {"effects": "Strength, courage, President/Prime Minister audience.", "unfavorable": "Cold fever, dysentery, coarse food.", "remedy": "Goat charity."},
        "Venus": {"effects": "Yog Triya Siddhi (accomplishment of rites), poetry composition.", "unfavorable": "Dental problems, heart disease, falling from a tree.", "remedy": "Durga Saptashati, cow."},
        "Sun": {"effects": "Employer favor, maternal/paternal home happiness.", "unfavorable": "Heart disease, lost articles, fevers.", "remedy": "Surya worship."},
        "Moon": {"effects": "Garments, family well-being.", "unfavorable": "Sleepiness, irregular meals, medicine administration.", "remedy": "Havan, jaggery/Ghi/curd-rice charity."},
        "Mars": {"effects": "Agriculture/cattle increase.", "unfavorable": "Gout, unnecessary expenditure, coarse food.", "remedy": "Havan, bull charity."},
        "Rahu": {"effects": "Elephants, garden construction.", "unfavorable": "Gout, bad dreams, continuous foreign journeys.", "remedy": "Mrityunjaya, goat."},
        "Jupiter": {"effects": "Vedas/Vedanta interest, sound health.", "unfavorable": "Leprosy, death of near relations, fines by government.", "remedy": "Shiva Sahasranam, gold."}
    },
    "Mercury": {
        "Mercury": {"effects": "Pearls, new kings meeting, piety.", "unfavorable": "Stomach pains, rheumatism.", "remedy": "Vishnu Sahasranam."},
        "Ketu": {"effects": "Industrial income, physical fitness.", "unfavorable": "Scorpions, menial quarrels.", "remedy": "Goat charity."},
        "Venus": {"effects": "Reservoir construction, religious rites readiness.", "unfavorable": "Heart disease, dysentery, defamation.", "remedy": "Durga Mantras."},
        "Sun": {"effects": "Land acquisition, sweet food.", "unfavorable": "Bilious troubles, headaches, weapons/fire danger.", "remedy": "Surya worship."},
        "Moon": {"effects": "Southward journeys, gems.", "unfavorable": "Wife-caused wealth loss, thieves, defamation.", "remedy": "Durga Mantras, clothes."},
        "Mars": {"effects": "Son's birth, property.", "unfavorable": "Gout, fever, wounds, weapon danger.", "remedy": "Mrityunjaya, cow."},
        "Rahu": {"effects": "Shrines, oblations.", "unfavorable": "Heart disease, hard government work, imprisonment.", "remedy": "Durga/Lakshmi, tawny cow."},
        "Jupiter": {"effects": "Sweetish preparations, Havan.", "unfavorable": "Snake/poison danger, disgrace, father's death.", "remedy": "Shiva Sahasranam, cow/gold."},
        "Saturn": {"effects": "Cattle increase, well-being.", "unfavorable": "Loss of thinking power, bad dreams, lethargy.", "remedy": "Mrityunjaya, black cow."}
    },
    "Ketu": {
        "Ketu": {"effects": "Land/village gain.", "unfavorable": "Instability of mind, heart disease, defamation.", "remedy": "Durga Saptashati, Mrityunjaya."},
        "Venus": {"effects": "King's reverence, sound health.", "unfavorable": "Headaches, eye troubles, uncaused quarrels.", "remedy": "Durga Path, tawny cow."},
        "Sun": {"effects": "Headship of small village.", "unfavorable": "Poison, foreign journeys, lunacy, fevers.", "remedy": "Cow/gold charity."},
        "Moon": {"effects": "Cows milk/curd increase, enthusiasm.", "unfavorable": "Business losses, anxiety.", "remedy": "Moon Mantras/charity."},
        "Mars": {"effects": "New gardens, king's wealth.", "unfavorable": "Diabetes, hunting death danger.", "remedy": "Bull charity."},
        "Rahu": {"effects": "Yavan king gains.", "unfavorable": "Frequent urination, cold/intermittent fever, opprobrium.", "remedy": "Durga Saptashati."},
        "Jupiter": {"effects": "Yagyas, son's birth.", "unfavorable": "Thieves, snakes, physical distress.", "remedy": "Mrityunjaya, Shiva Sahasranam."},
        "Saturn": {"effects": "Employer happiness.", "unfavorable": "Fine imposition, resignation from post, lethargy.", "remedy": "Sesame Havan, black cow."},
        "Mercury": {"effects": "Poetry association, religious discourses.", "unfavorable": "Residing in other people's houses, cattle destruction.", "remedy": "Vishnu Sahasranam."}
    },
    "Venus": {
        "Venus": {"effects": "Brahmins' wealth, daily sweet preparations, Westward journey garments.", "unfavorable": "Thieves, official antagonism.", "remedy": "Durga Path, cow."},
        "Sun": {"effects": "Fortune betterment, fame.", "unfavorable": "Harsh language, father's distress, wrath.", "remedy": "Surya worship."},
        "Moon": {"effects": "Musician association, buffaloes, dining with brothers.", "unfavorable": "Foreign journeys, physical distress.", "remedy": "None specified."},
        "Mars": {"effects": "Desired objects, land.", "unfavorable": "Cold fever, parents' diseases, extravagant expenditure.", "remedy": "None specified."},
        "Rahu": {"effects": "Successful foreign journeys, enthusiasm.", "unfavorable": "Indigestion, fever, poison.", "remedy": "Mrityunjaya."},
        "Jupiter": {"effects": "Shastras industriousness, friend's reverence.", "unfavorable": "Thieves, disease danger.", "remedy": "Mrityunjaya."},
        "Saturn": {"effects": "Daughter's birth, shrines.", "unfavorable": "Lethargy, expenditure exceeding income, foreign travel.", "remedy": "Sesame Havan, Mrityunjaya."},
        "Mercury": {"effects": "Court judgement wealth, Purana stories.", "unfavorable": "Residing in others' houses, cattle loss, fever.", "remedy": "Vishnu Sahasranam."},
        "Ketu": {"effects": "Sweetish preparations, victory in war.", "unfavorable": "Loss of thinking power, diabetes, uncaused quarrels.", "remedy": "Mrityunjaya, goat."}
    }
}

# ==============================================================================
# SECTION 4: PRATYANTAR EFFECTS (Sub-Sub-Periods)
# ==============================================================================
PRATYANTAR = {
    "Sun": {"Sun": "Argument, headache", "Moon": "Excitement, quarrels", "Mars": "Weapons/fire danger", "Rahu": "Phlegm, kingdom fall", "Jupiter": "Gold, vehicles", "Saturn": "Cattle distress", "Mercury": "Religious mind", "Ketu": "Death fear", "Venus": "Moderate wealth"},
    "Moon": {"Moon": "Sweet preparations, land", "Mars": "Wisdom, public reverence", "Rahu": "Well-being or death if malefic", "Jupiter": "Preceptor knowledge, glory", "Saturn": "Bilious troubles", "Mercury": "White garments, son", "Ketu": "Brahmin quarrels", "Venus": "Daughter, sweets", "Sun": "Victories"},
    "Mars": {"Mars": "Blood diseases, premature death", "Rahu": "Unpalatable food, fall of government", "Jupiter": "Intelligence loss, child sorrow", "Saturn": "Employer destruction, anxiety", "Mercury": "Fevers, friend loss", "Ketu": "Lethargy, weapon danger", "Venus": "Chandal distress, vomiting", "Sun": "Property increase", "Moon": "Southward garments, success"},
    "Rahu": {"Rahu": "Weapon injury, jail", "Jupiter": "Elephants, wealth", "Saturn": "Rigorous jail, rheumatism", "Mercury": "Abnormal wife gains", "Ketu": "Intelligence loss, obstacles", "Venus": "Yogini danger, unpalatable food", "Sun": "Fevers, negligence", "Moon": "Reputation loss, father distress", "Mars": "Septic boil in anus/Bhagandhar, blood pollution"},
    "Jupiter": {"Jupiter": "Gold", "Saturn": "Iron, camels, sesame", "Mercury": "Pearls, education", "Ketu": "Water/thief danger", "Venus": "Learning, ornaments", "Sun": "Parents' gain", "Moon": "No distress", "Mars": "Stomach burning, anus pain", "Rahu": "Chandal/menial antagonism"},
    "Saturn": {"Saturn": "Physical distress", "Mercury": "Food anxiety", "Ketu": "Imprisonment in enemy camp, hunger", "Venus": "Ambition fulfillment", "Sun": "Fevers, family quarrels", "Moon": "Extravagance, many women", "Mars": "Fire, wind/bile", "Rahu": "Foreign, death fear", "Jupiter": "Women-caused losses"},
    "Mercury": {"Mercury": "Intellect, clothes", "Ketu": "Coarse food, eye/blood troubles", "Venus": "Northern gains, cattle loss", "Sun": "Heart distress, splendor loss", "Moon": "Daughter's birth, marriage", "Mars": "Red clothes, fire danger", "Rahu": "Women danger, king's wrath", "Jupiter": "Kingdom, intelligence", "Saturn": "Wind/bile, body injuries"},
    "Ketu": {"Ketu": "Sudden disaster, foreign", "Venus": "Non-Hindu king loss, headache", "Sun": "Defeat, argument", "Moon": "Dysentery, grains loss", "Mars": "Weapons, menial danger", "Rahu": "Women/menial distress", "Jupiter": "Opprobrium, friend loss", "Saturn": "Cattle death", "Mercury": "Intelligence loss, excitement"},
    "Venus": {"Venus": "White clothes, beautiful damsels", "Sun": "Rheumatic fever, headache", "Moon": "King's clothes, daughter", "Mars": "Blood/bile", "Rahu": "Wife quarrels", "Jupiter": "Elephants, gems", "Saturn": "Donkey, camel, goat, iron", "Mercury": "Wealth distributed by others", "Ketu": "Homeland departure, death fear"}
}