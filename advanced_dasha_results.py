# advanced_dasha_results.py
# Comprehensive database for all classical Dasha effects.

MAHADASHA_GENERAL = {
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
        "favorable": "Wealth, agriculture, new house construction, religious inclination, foreign government recognition, and clothes.",
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
        "unfavorable": "Defamation, cattle destruction, wife distress, and business losses."
    }
}

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

VIM_ANTAR_EFFECTS = {
    "Sun": {
        "Sun": {"effect": "Wealth, grains.", "weak": "Premature death (if 2nd/7th lord).", "remedy": "Mrityunjaya Japa / Sun worship."},
        "Moon": {"effect": "Marriage, son's birth, house, cattle, king's favor.", "weak": "Wife/children distress, jail, urinary troubles, bad food, coparcener disputes.", "remedy": "White cow/female buffalo charity."},
        "Mars": {"effect": "Land, army commander position, destruction of enemies.", "weak": "Brutality, mental ailment, jail, brother disputes.", "remedy": "Vedas recitation, Vrashotsarg."},
        "Rahu": {"effect": "First 2 months: Thieves, snake danger, wounds. Later: Fame, son's birth, king's favor.", "weak": "Dysentery, skin enlargement (Gulma), destroyed house.", "remedy": "Durga worship, black cow."},
        "Jupiter": {"effect": "Palanquin comforts, kingdom, religious oblations.", "weak": "Sinful deeds, king's displeasure, body pains.", "remedy": "Kapila cow (tawny), gold charity."},
        "Saturn": {"effect": "Foes destroyed, wealth from many sources, fame.", "weak": "Rheumatism, dysentery, rigorous jail, claimant disputes, separation from parents.", "remedy": "Black cow, goat charity."},
        "Mercury": {"effect": "Indra-like happiness, sweet drinks, pearls, corals, assumed names.", "weak": "Jaundice, urinary issues, body distress, foreign exile.", "remedy": "Vishnu Sahasranam, silver idol."},
        "Ketu": {"effect": "Satisfaction, clothes.", "weak": "Tooth/cheek diseases, lost position, father's death.", "remedy": "Shat Chandi Path, goat charity."},
        "Venus": {"effect": "Pearls, musical instruments, sweet food daily, cattle.", "weak": "Dysentery, fevers, wife distress.", "remedy": "Rudra Japa, tawny cow."}
    },
    "Moon": {
        "Moon": {"effect": "Horses, elephants, divine devotion, kingship.", "weak": "Lethargy, mother's distress, jail, body pains.", "remedy": "Tawny cow charity."},
        "Mars": {"effect": "Ornaments, agriculture increase, fortune.", "weak": "Employee antagonism, home losses, hot temperament.", "remedy": "Bull charity."},
        "Rahu": {"effect": "Gains from South-West, holy pilgrimages.", "weak": "Scorpions, snakes, loss of reputation.", "remedy": "Rahu Japa, goat."},
        "Jupiter": {"effect": "Isht Devata beneficence, kingdom, marriage.", "weak": "Preceptor/father's death, unpalatable food, lost property.", "remedy": "Shiva Sahasranam, gold."},
        "Saturn": {"effect": "Sudra assistance, agricultural profits, son's birth.", "weak": "Holy river bathing (due to distress), enemy troubles.", "remedy": "Mrityunjaya, black cow."},
        "Mercury": {"effect": "Soma Rasa (tasty syrups), pearls, Shastra discussions.", "weak": "Jail, agriculture loss, fever fears.", "remedy": "Vishnu Sahasranam, goat."},
        "Ketu": {"effect": "Wealth, religious inclination.", "weak": "Enemy interference, body afflictions.", "remedy": "Mrityunjaya Japa."},
        "Venus": {"effect": "Sweet preparations daily, beautiful women, underground hidden treasure.", "weak": "Deportation, snake/thief danger.", "remedy": "Rudra Japa, white cow, silver."},
        "Sun": {"effect": "Kingdom recovery, village acquisition, friend assistance.", "weak": "Snake/poison danger, fever, foreign travel troubles.", "remedy": "Shiva worship."}
    },
    "Mars": {
        "Mars": {"effect": "Lakshmi's beneficence, kingdom recovery, buffalo/cow gains.", "weak": "Urinary troubles, wounds, snake danger.", "remedy": "Rudra Japa, red bull."},
        "Rahu": {"effect": "Ganges bathing, foreign journeys.", "weak": "Wind/bile disease, snake danger, goblins.", "remedy": "Naga Puja, Mrityunjaya."},
        "Jupiter": {"effect": "Good health, reputation, property.", "weak": "Goblins (Pret), bilious diseases, servant loss.", "remedy": "Shiva Sahasranam."},
        "Saturn": {"effect": "Grandchildren, cow increase.", "weak": "Yavana kings danger, war defeat, urinary troubles.", "remedy": "Black cow charity."},
        "Mercury": {"effect": "Pious persons association, sweetish preparations, commander role.", "weak": "Heart disease, harsh speech, dacoits during travel.", "remedy": "Vishnu Sahasranam, horse charity."},
        "Ketu": {"effect": "Commander position, employer wealth, oblations.", "weak": "Tooth trouble, tiger/thief distress, leprosy, dysentery.", "remedy": "Goat charity."},
        "Venus": {"effect": "Elephants, horses, perfumery, wells/reservoirs construction.", "weak": "Family dissensions, cattle destruction.", "remedy": "Cow/buffalo charity."},
        "Sun": {"effect": "Potency, business profits, king audience.", "weak": "Forehead troubles, fever, dysentery.", "remedy": "Surya worship."},
        "Moon": {"effect": "Perfumes, marriage, parents' good relations.", "weak": "War danger, death, mental agony.", "remedy": "Durga/Lakshmi Mantras."}
    },
    "Rahu": {
        "Rahu": {"effect": "Kingdom, enthusiasm, cordial king relations.", "weak": "Wounds, official antagonism, disease.", "remedy": "Rahu worship/charity."},
        "Jupiter": {"effect": "Candr-like wealth growth, South-East journeys, good food, devotion.", "weak": "Heart disease, defamation.", "remedy": "Shiva/gold."},
        "Saturn": {"effect": "Garden construction, Sudra wealth, sudden ornament gains.", "weak": "Menial danger, Gulma affliction, unpalatable food.", "remedy": "Black cow/she-buffalo."},
        "Mercury": {"effect": "Wednesday Raj Yog, bed/women comforts, Purana discourses.", "weak": "Speaking lies, snake/thief fears, deity opprobrium.", "remedy": "Vishnu Sahasranam."},
        "Ketu": {"effect": "Rheumatic fever, foreign journeys, gold acquisition.", "weak": "Wounds, parental separation, body distress.", "remedy": "Goat charity."},
        "Venus": {"effect": "Sacred thread (Janou) ceremony, sweet food, house construction.", "weak": "Employer death danger, stomach pain, diabetes, blood pollution.", "remedy": "Durga/Lakshmi worship."},
        "Sun": {"effect": "Village headship, foreign recognition, elephants.", "weak": "Fevers, dysentery, travels.", "remedy": "Surya worship."},
        "Moon": {"effect": "Property increase, deity worship.", "weak": "Evil spirits, leopards, wild animals, stomach disorders.", "remedy": "White cow/female buffalo."},
        "Mars": {"effect": "Red garments, commander role.", "weak": "Wife/child antagonism, wounds, lethargy.", "remedy": "Cow/bull charity."}
    },
    "Jupiter": {
        "Jupiter": {"effect": "Sovereignty, blue-colored horse gains, Westward journeys.", "weak": "Menial association, coparcener slander.", "remedy": "Rudr/Shiva Sahasranam."},
        "Saturn": {"effect": "Enemy property acquisition.", "weak": "Fever, wound infliction, employment loss.", "remedy": "Vishnu Sahasranam, black cow."},
        "Mercury": {"effect": "Conveyances.", "weak": "Fever, dysentery, foreign wanderings, burning sensations.", "remedy": "Vishnu Sahasranam."},
        "Ketu": {"effect": "Palanquin, Muslim king (Yavana) wealth.", "weak": "Coarse food, death ceremonies food, king's wrath.", "remedy": "Mrityunjaya."},
        "Venus": {"effect": "Blue/red articles, Eastward extraordinary income, music society.", "weak": "Father-in-law disputes, snake/king wrath.", "remedy": "Tawny cow/buffalo."},
        "Sun": {"effect": "Glory, children increase.", "weak": "Nervous disorder, sins, reluctance to good deeds.", "remedy": "Adhitya Hridaya Path."},
        "Moon": {"effect": "Good food, grandchildren, religious inclinations.", "weak": "Maternal uncle separation, coparcener quarrels.", "remedy": "Durga Saptashati."},
        "Mars": {"effect": "Marriage, strength/valor, sweetish preparations.", "weak": "Eye trouble, house loss.", "remedy": "Bull charity."},
        "Rahu": {"effect": "Village sovereignty, holy bathing.", "weak": "Goblins, bad dreams, snakes.", "remedy": "Mrityunjaya, goat."}
    },
    "Saturn": {
        "Saturn": {"effect": "Commander role, elephants.", "weak": "Bleeding gums, dysentery, weapon injuries.", "remedy": "Mrityunjaya."},
        "Mercury": {"effect": "Yagyas, Puranas listening, sweet preparations.", "weak": "Business failures, anxiety.", "remedy": "Vishnu Sahasranam, grains."},
        "Ketu": {"effect": "Strength, courage, President/Prime Minister audience.", "weak": "Cold fever, dysentery, coarse food.", "remedy": "Goat charity."},
        "Venus": {"effect": "Yog Triya Siddhi, poetry composition.", "weak": "Dental problems, heart disease, falling from tree, drowning.", "remedy": "Durga Saptashati, cow."},
        "Sun": {"effect": "Employer favor, maternal/paternal home happiness.", "weak": "Heart disease, lost articles, fevers.", "remedy": "Surya worship."},
        "Moon": {"effect": "Garments, family well-being.", "weak": "Sleepiness, lethargy, irregular meals.", "remedy": "Havan, jaggery/Ghi/curd-rice charity."},
        "Mars": {"effect": "Agriculture/cattle increase.", "weak": "Gout, unnecessary expenditure, coarse food.", "remedy": "Havan, bull charity."},
        "Rahu": {"effect": "Elephants, garden construction.", "weak": "Gout, bad dreams, continuous foreign journeys.", "remedy": "Mrityunjaya, goat."},
        "Jupiter": {"effect": "Vedas/Vedanta interest, sound health.", "weak": "Leprosy, death of near relations, fines by government.", "remedy": "Shiva Sahasranam, gold."}
    },
    "Mercury": {
        "Mercury": {"effect": "Pearls, new kings meeting, piety.", "weak": "Stomach pains, rheumatism.", "remedy": "Vishnu Sahasranam."},
        "Ketu": {"effect": "Industrial income, physical fitness.", "weak": "Scorpions, menial quarrels.", "remedy": "Goat charity."},
        "Venus": {"effect": "Reservoir construction, religious rites readiness.", "weak": "Heart disease, dysentery, defamation.", "remedy": "Durga Mantras."},
        "Sun": {"effect": "Land acquisition, sweet food.", "weak": "Bilious troubles, headaches, weapons/fire danger.", "remedy": "Surya worship."},
        "Moon": {"effect": "Southward journeys, gems.", "weak": "Wife-caused wealth loss, thieves, defamation.", "remedy": "Durga Mantras, clothes."},
        "Mars": {"effect": "Son's birth, property.", "weak": "Gout, fever, wounds, weapon danger.", "remedy": "Mrityunjaya, cow."},
        "Rahu": {"effect": "Shrines, oblations.", "weak": "Heart disease, hard government work, imprisonment.", "remedy": "Durga/Lakshmi, tawny cow."},
        "Jupiter": {"effect": "Sweetish preparations, Havan.", "weak": "Snake/poison danger, disgrace, father's death.", "remedy": "Shiva Sahasranam, cow/gold."},
        "Saturn": {"effect": "Cattle increase, well-being.", "weak": "Loss of thinking power, bad dreams, lethargy.", "remedy": "Mrityunjaya, black cow."}
    },
    "Ketu": {
        "Ketu": {"effect": "Land/village gain.", "weak": "Instability of mind, heart disease, defamation.", "remedy": "Durga Saptashati, Mrityunjaya."},
        "Venus": {"effect": "King's reverence, sound health.", "weak": "Headaches, eye troubles, uncaused quarrels.", "remedy": "Durga Path, tawny cow."},
        "Sun": {"effect": "Headship of small village.", "weak": "Poison, foreign journeys, lunacy, fevers.", "remedy": "Cow/gold charity."},
        "Moon": {"effect": "Cows milk/curd increase, enthusiasm.", "weak": "Business losses, anxiety.", "remedy": "Moon Mantras/charity."},
        "Mars": {"effect": "New gardens, king's wealth.", "weak": "Diabetes, hunting death danger.", "remedy": "Bull charity."},
        "Rahu": {"effect": "Yavan king gains.", "weak": "Frequent urination, cold/intermittent fever, opprobrium.", "remedy": "Durga Saptashati."},
        "Jupiter": {"effect": "Yagyas, son's birth.", "weak": "Thieves, snakes, physical distress.", "remedy": "Mrityunjaya, Shiva Sahasranam."},
        "Saturn": {"effect": "Employer happiness.", "weak": "Fine imposition, resignation from post, lethargy.", "remedy": "Sesame Havan, black cow."},
        "Mercury": {"effect": "Poetry association, religious discourses.", "weak": "Residing in other people's houses, cattle destruction.", "remedy": "Vishnu Sahasranam."}
    },
    "Venus": {
        "Venus": {"effect": "Brahmins' wealth, daily sweet preparations, Westward journey garments.", "weak": "Thieves, official antagonism.", "remedy": "Durga Path, cow."},
        "Sun": {"effect": "Fortune betterment, fame.", "weak": "Harsh language, father's distress, wrath.", "remedy": "Surya worship."},
        "Moon": {"effect": "Musician association, buffaloes, dining with brothers.", "weak": "Foreign journeys, physical distress.", "remedy": "Moon Mantras."},
        "Mars": {"effect": "Desired objects, land.", "weak": "Cold fever, parents' diseases, extravagant expenditure.", "remedy": "Bull charity."},
        "Rahu": {"effect": "Successful foreign journeys, enthusiasm.", "weak": "Indigestion, fever, poison.", "remedy": "Mrityunjaya."},
        "Jupiter": {"effect": "Shastras industriousness, friend's reverence.", "weak": "Thieves, disease danger.", "remedy": "Mrityunjaya."},
        "Saturn": {"effect": "Daughter's birth, shrines.", "weak": "Lethargy, expenditure exceeding income, foreign travel.", "remedy": "Sesame Havan, Mrityunjaya."},
        "Mercury": {"effect": "Court judgement wealth, Purana stories.", "weak": "Residing in others' houses, cattle loss, fever.", "remedy": "Vishnu Sahasranam."},
        "Ketu": {"effect": "Sweetish preparations, victory in war.", "weak": "Loss of thinking power, diabetes, uncaused quarrels.", "remedy": "Mrityunjaya, goat."}
    }
}

PRATYANTAR_EFFECTS = {
    "Sun": {"Sun": "Argument, headache", "Moon": "Excitement, quarrels", "Mars": "Weapons/fire danger", "Rahu": "Phlegm, kingdom fall", "Jupiter": "Gold, vehicles", "Saturn": "Cattle distress", "Mercury": "Religious mind", "Ketu": "Death fear", "Venus": "Moderate wealth"},
    "Moon": {"Moon": "Sweet preparations, land", "Mars": "Wisdom, public reverence", "Rahu": "Well-being or death if malefic", "Jupiter": "Preceptor knowledge, glory", "Saturn": "Bilious troubles", "Mercury": "White garments, son", "Ketu": "Brahmin quarrels", "Venus": "Daughter, sweets", "Sun": "Victories"},
    "Mars": {"Mars": "Blood diseases, premature death", "Rahu": "Unpalatable food, fall of government", "Jupiter": "Intelligence loss, child sorrow", "Saturn": "Employer destruction, anxiety", "Mercury": "Fevers, friend loss", "Ketu": "Lethargy, weapon danger", "Venus": "Chandal distress, vomiting", "Sun": "Property increase", "Moon": "Southward garments, success"},
    "Rahu": {"Rahu": "Weapon injury, jail", "Jupiter": "Elephants, wealth", "Saturn": "Rigorous jail, rheumatism", "Mercury": "Abnormal wife gains", "Ketu": "Intelligence loss, obstacles", "Venus": "Yogini danger, unpalatable food", "Sun": "Fevers, negligence", "Moon": "Reputation loss, father distress", "Mars": "Septic boil, blood pollution"},
    "Jupiter": {"Jupiter": "Gold", "Saturn": "Iron, camels, sesame", "Mercury": "Pearls, education", "Ketu": "Water/thief danger", "Venus": "Learning, ornaments", "Sun": "Parents' gain", "Moon": "No distress", "Mars": "Stomach burning, anus pain", "Rahu": "Chandal/menial antagonism"},
    "Saturn": {"Saturn": "Physical distress", "Mercury": "Food anxiety", "Ketu": "Imprisonment in enemy camp, hunger", "Venus": "Ambition fulfillment", "Sun": "Fevers, family quarrels", "Moon": "Extravagance, many women", "Mars": "Fire, wind/bile", "Rahu": "Foreign, death fear", "Jupiter": "Women-caused losses"},
    "Mercury": {"Mercury": "Intellect, clothes", "Ketu": "Coarse food, eye/blood troubles", "Venus": "Northern gains, cattle loss", "Sun": "Heart distress, splendor loss", "Moon": "Daughter's birth, marriage", "Mars": "Red clothes, fire danger", "Rahu": "Women danger, king's wrath", "Jupiter": "Kingdom, intelligence", "Saturn": "Wind/bile, body injuries"},
    "Ketu": {"Ketu": "Sudden disaster, foreign", "Venus": "Non-Hindu king loss, headache", "Sun": "Defeat, argument", "Moon": "Dysentery, grains loss", "Mars": "Weapons, menial danger", "Rahu": "Women/menial distress", "Jupiter": "Opprobrium, friend loss", "Saturn": "Cattle death", "Mercury": "Intelligence loss, excitement"},
    "Venus": {"Venus": "White clothes, beautiful damsels", "Sun": "Rheumatic fever, headache", "Moon": "King's clothes, daughter", "Mars": "Blood/bile", "Rahu": "Wife quarrels", "Jupiter": "Elephants, gems", "Saturn": "Donkey, camel, goat, iron", "Mercury": "Wealth distributed by others", "Ketu": "Homeland departure, death fear"}
}