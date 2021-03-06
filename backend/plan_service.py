from flask import Blueprint, request, jsonify
import pymongo
import random

from goals_service import calculate_tdee_macros

from auth_service import verify_credentials, get_id_from_request

plan_service = Blueprint("plan_service", __name__)

client = pymongo.MongoClient(
    "mongodb+srv://sushil:sushil@foodcluster-trclg.mongodb.net/test?retryWrites=true&w=majority"
)
db = client.foods.food_data

client_user = pymongo.MongoClient(
    "mongodb+srv://connor:connor@foodcluster-trclg.mongodb.net/test?retryWrites=true&w=majority"
)
db_user = client_user.users.users_info

db_user_history = client_user.users.users_history

"""
Function: get_daily_plan

Returns a daily_plan object to front end. This object is a Dict with keys as meals,
values as lists of meal objects (which themselves are dicts comntaining food info)
"""


@plan_service.route("/api/users/plan/get_daily_meals", methods=["POST"])
def get_daily_meals():
    if not verify_credentials(request):
        return "Unauthorized: Invalid or missing credentials", 401
    params = request.json

    user_id = get_id_from_request(request)
    if not user_id:
        return "No user found", 400

    if not params or "date" not in params:
        return "Please include the date", 400
    given_date = str(params["date"])

    # save to date in user_history db
    user_history = db_user_history.find_one({"user_id": user_id})
    if not user_history:  # doesn't exist yet so create
        new_history = {"user_id": user_id, "history": {}}
        db_user_history.insert_one(new_history)
        user_history = db_user_history.find_one({"user_id": user_id})
    
    # DAILY PLAN GENERATOR
    dailyPlan = generateDailyMeals(user_id, given_date, user_history)

    # go through daily plan for bfast, lunch, dinner, snacks, and one by one add
    dateObject = {}
    # Breakfast
    breakfastObject = {}
    breakfast = dailyPlan["Breakfast"]
    for food in breakfast:
        breakfastObject[str(food["food_id"])] = round(food["Servings"], 1)
    dateObject["Breakfast"] = breakfastObject
    # Lunch
    lunchObject = {}
    lunch = dailyPlan["Lunch"]
    for food in lunch:
        lunchObject[str(food["food_id"])] = round(food["Servings"], 1)
    dateObject["Lunch"] = lunchObject
    # Dinner
    dinnerObject = {}
    dinner = dailyPlan["Dinner"]
    for food in dinner:
        dinnerObject[str(food["food_id"])] = round(food["Servings"], 1)
    dateObject["Dinner"] = dinnerObject
    # Snacks
    dateObject["Snacks"] = {}

    # add to user_history
    currHistoryObject = user_history.get("history", {})
    currHistoryObject[
        given_date
    ] = dateObject  # hardcoded date for now b/c frontend isn't passing in date
    db_user_history.update_one(
        {"user_id": user_id}, {"$set": {"history": currHistoryObject}}
    )

    print(dailyPlan)
    return jsonify(dailyPlan)


"""
Function: generateDailyMeals

Given a user identifier and a date, finds the user's prescribed calories for their personal plan and
generates meals for the given day given the user's constraints.

Arguments:
user_id (int) : identifier for the user
date (string) : the date for which meals should be generated

Returns:
(object) : list of meals for the given day
"""


def generateDailyMeals(user_id, date, user_history):
    # get macros
    proteinGroups = [
        "Sausages and Luncheon Meats",
        "Poultry Products",
        "Pork Products",
        "Legumes and Legume Products",
        "Lamb, Veal, and Game Products",
        "Finfish and Shellfish Products",
        "Dairy and Egg Products",
        "Beef Products",
    ]
    fatGroups = ["Nut and Seed Products", "Fats and Oils"]
    carbGroups = [
        "Vegetables and Vegetable Products",
        "Sweets",
        "Fruits and Fruit Juices",
        "Cereal Grains and Pasta",
        "Breakfast Cereals",
    ]
    RESTRICTIONS_MAP = {
        "Vegan": {
            "Sausages and Luncheon Meats",
            "Poultry Products",
            "Pork Products",
            "Lamb, Veal, and Game Products",
            "Finfish and Shellfish Products",
            "Fats and Oils",
            "Dairy and Egg Products",
            "Beef Products",
        },
        "Vegetarian": {
            "Sausages and Luncheon Meats",
            "Poultry Products",
            "Pork Products",
            "Lamb, Veal, and Game Products",
            "Finfish and Shellfish Products",
            "Beef Products",
        },
        "Pescatarian": {
            "Sausages and Luncheon Meats",
            "Poultry Products",
            "Pork Products",
            "Lamb, Veal, and Game Products",
            "Beef Products",
        },
        "No Red Meat": {
            "Sausages and Luncheon Meats",
            "Lamb, Veal, and Game Products",
            "Beef Products",
        },
        "No Pork": {"Pork Products"},
        "No Beef": {"Beef Products"},
        "Nut Allergy": {"Legumes and Legume Products", "Nut and Seed Products"},
    }
    user_info = db_user.find_one({"user_id": user_id})

    # CALCULATE TEMPLATES BASED ON RESTRICTIONS
    print(proteinGroups)
    restrictions = user_info["restrictions"]
    if len(restrictions) != 0:  # has restrictions
        for restriction in restrictions:
            # protein
            i = 0
            while i < len(proteinGroups):
                food = proteinGroups[i]
                if food in RESTRICTIONS_MAP[restriction]:  # bad food
                    proteinGroups.remove(food)
                else:
                    i += 1
            # carbs
            i = 0
            while i < len(carbGroups):
                food = carbGroups[i]
                if food in RESTRICTIONS_MAP[restriction]:  # bad food
                    carbGroups.remove(food)
                else:
                    i += 1
            # fat
            i = 0
            while i < len(fatGroups):
                food = fatGroups[i]
                if food in RESTRICTIONS_MAP[restriction]:  # bad food
                    fatGroups.remove(food)
                else:
                    i += 1

    print(proteinGroups)
    macros = calculate_tdee_macros(user_info)
    calories = macros["tdee"]

    mealTemplate1 = [
        random.choice(proteinGroups),
        random.choice(carbGroups),
        random.choice(fatGroups),
    ]
    mealTemplate2 = [
        random.choice(proteinGroups),
        random.choice(carbGroups),
        random.choice(fatGroups),
    ]
    mealTemplate3 = [
        random.choice(proteinGroups),
        random.choice(carbGroups),
        random.choice(fatGroups),
    ]

    return generateDailyMeals_Cals(
        calories, mealTemplate1, mealTemplate2, mealTemplate3, date, user_id, user_history
    )


"""
Function: generateDailyMeals_cals

Given three meal templates (list of food groups) and the user's maximum calories per day, creates a meal for breakfast, lunch,
and dinner and relevant serving sizes.

Arguments:
calories (int) : the calories the user should consume in a given day
template1 (object) : [Protein Food Group, Carb Food Group, Fat Food Group]
template2 (object) : [Protein Food Group, Carb Food Group, Fat Food Group]
template3 (object) : [Protein Food Group, Carb Food Group, Fat Food Group]
date (string) : date for which the meals are generated
user_id (int) : identifier for the user

Returns:
(object) : list of meals for the given day
"""


def generateDailyMeals_Cals(calories, template1, template2, template3, date, user_id, user_history):
    caloriesPerMeal = calories / 3
    dailyPlan = {}
    # STEP 1: GENERATE MEALS AND ADJUST SERVING SIZES BASED ON CALORIES
    # BREAKFAST
    breakfast = generateMeal(template1, date, user_id, user_history)
    serving1 = (0.5 * caloriesPerMeal) / (breakfast[0][1][3])
    breakfast[0][1][0] = breakfast[0][1][0] * float(serving1)
    breakfast[0][1][1] = breakfast[0][1][1] * float(serving1)
    breakfast[0][1][2] = breakfast[0][1][2] * float(serving1)
    breakfast[0][1][3] = breakfast[0][1][3] * float(serving1)
    breakfast[0][1].append(serving1)

    serving2 = (0.25 * caloriesPerMeal) / (breakfast[1][1][3])
    breakfast[1][1][0] = breakfast[1][1][0] * float(serving2)
    breakfast[1][1][1] = breakfast[1][1][1] * float(serving2)
    breakfast[1][1][2] = breakfast[1][1][2] * float(serving2)
    breakfast[1][1][3] = breakfast[1][1][3] * float(serving2)
    breakfast[1][1].append(serving2)

    serving3 = (0.25 * caloriesPerMeal) / (breakfast[2][1][3])
    breakfast[2][1][0] = breakfast[2][1][0] * float(serving3)
    breakfast[2][1][1] = breakfast[2][1][1] * float(serving3)
    breakfast[2][1][2] = breakfast[2][1][2] * float(serving3)
    breakfast[2][1][3] = breakfast[2][1][3] * float(serving3)
    breakfast[2][1].append(serving3)
    #     print(breakfast)

    # LUNCH
    lunch = generateMeal(template2, date, user_id, user_history)
    serving1 = (0.5 * caloriesPerMeal) / (lunch[0][1][3])
    lunch[0][1][0] = lunch[0][1][0] * float(serving1)
    lunch[0][1][1] = lunch[0][1][1] * float(serving1)
    lunch[0][1][2] = lunch[0][1][2] * float(serving1)
    lunch[0][1][3] = lunch[0][1][3] * float(serving1)
    lunch[0][1].append(serving1)

    serving2 = (0.25 * caloriesPerMeal) / (lunch[1][1][3])
    lunch[1][1][0] = lunch[1][1][0] * float(serving2)
    lunch[1][1][1] = lunch[1][1][1] * float(serving2)
    lunch[1][1][2] = lunch[1][1][2] * float(serving2)
    lunch[1][1][3] = lunch[1][1][3] * float(serving2)
    lunch[1][1].append(serving2)

    serving3 = (0.25 * caloriesPerMeal) / (lunch[2][1][3])
    lunch[2][1][0] = lunch[2][1][0] * float(serving3)
    lunch[2][1][1] = lunch[2][1][1] * float(serving3)
    lunch[2][1][2] = lunch[2][1][2] * float(serving3)
    lunch[2][1][3] = lunch[2][1][3] * float(serving3)
    lunch[2][1].append(serving3)
    #     print(lunch)

    # DINNER
    dinner = generateMeal(template3, date, user_id, user_history)
    serving1 = (0.5 * caloriesPerMeal) / (dinner[0][1][3])
    dinner[0][1][0] = dinner[0][1][0] * float(serving1)
    dinner[0][1][1] = dinner[0][1][1] * float(serving1)
    dinner[0][1][2] = dinner[0][1][2] * float(serving1)
    dinner[0][1][3] = dinner[0][1][3] * float(serving1)
    dinner[0][1].append(serving1)

    serving2 = (0.25 * caloriesPerMeal) / (dinner[1][1][3])
    dinner[1][1][0] = dinner[1][1][0] * float(serving2)
    dinner[1][1][1] = dinner[1][1][1] * float(serving2)
    dinner[1][1][2] = dinner[1][1][2] * float(serving2)
    dinner[1][1][3] = dinner[1][1][3] * float(serving2)
    dinner[1][1].append(serving2)

    serving3 = (0.25 * caloriesPerMeal) / (dinner[2][1][3])
    dinner[2][1][0] = dinner[2][1][0] * float(serving3)
    dinner[2][1][1] = dinner[2][1][1] * float(serving3)
    dinner[2][1][2] = dinner[2][1][2] * float(serving3)
    dinner[2][1][3] = dinner[2][1][3] * float(serving3)
    dinner[2][1].append(serving3)
    #     print(dinner)

    # STEP 2: REFORMAT MEALS
    return reformatDay(breakfast, lunch, dinner)


"""
Function: reformatMeal

Helper function to reformat a series of meals to the format expected on the frontend.

Arguments:
meal1 (object) : the generated breakfast meal
meal2 (object) : the generated lunch meal
meal3 (object) : the generated dinner meal

Returns:
(object) : list of meals for the given day
"""


def reformatDay(meal1, meal2, meal3):
    dailyPlan = {}

    # Breakfast
    foodList = []
    for food in meal1:
        foodDict = {}
        foodDict["food_id"] = food[2]
        foodDict["Food Name"] = food[0]
        foodDict["Protein"] = food[1][0]
        foodDict["Fat"] = food[1][1]
        foodDict["Carb"] = food[1][2]
        foodDict["Calories"] = food[1][3]
        foodDict["Servings"] = food[1][4]
        foodList.append(foodDict)
    dailyPlan["Breakfast"] = foodList
    # Lunch
    foodList = []
    for food in meal2:
        foodDict = {}
        foodDict["food_id"] = food[2]
        foodDict["Food Name"] = food[0]
        foodDict["Protein"] = food[1][0]
        foodDict["Fat"] = food[1][1]
        foodDict["Carb"] = food[1][2]
        foodDict["Calories"] = food[1][3]
        foodDict["Servings"] = food[1][4]
        foodList.append(foodDict)
    dailyPlan["Lunch"] = foodList
    # Dinner
    foodList = []
    for food in meal3:
        foodDict = {}
        foodDict["food_id"] = food[2]
        foodDict["Food Name"] = food[0]
        foodDict["Protein"] = food[1][0]
        foodDict["Fat"] = food[1][1]
        foodDict["Carb"] = food[1][2]
        foodDict["Calories"] = food[1][3]
        foodDict["Servings"] = food[1][4]
        foodList.append(foodDict)
    dailyPlan["Dinner"] = foodList
    dailyPlan["Snacks"] = []
    return dailyPlan


"""
Function: reformatMeal

Chooses foods for a meal given a template specifying which food groups to generate.

Arguments:
template (object) : [Protein Food Group, Carb Food Group, Fat Food Group]
user_id (int) : identifier for the user

Returns:
(object) : the generated meal
"""


def generateMeal(template, date, user_id, user_history):
	meal = []
	recentFoods = fetchRecentFoods(user_id, date, user_history)
	for group in template:
		matches = db.find({"Food Group": group})
		length = matches.count()
		randomNumber = random.randint(1, length)
		count = 1
		for x in matches:
			if count == randomNumber:
				if x["food_id"] in recentFoods: #we have recently recommended this food, so try again
					randomNumber += 1
				meal.append([x["Food Name"], get_important_macros(x), x["food_id"]])
				break
			count += 1
	return meal



"""
Function: fetchRecentFoods

Looks at the user history db for a list of foods recently recommended to the user. (previous day)

Arguments:
user_id (int) : identifier for the user
date (string) : Date for which the meals are generated

Returns:
(list) : the list of foods
"""


def fetchRecentFoods(user_id, date, user_history):
	recentFoods = []
	currHistoryObject = user_history.get("history", {})

	#math to get the string date for yesterday
	prevDate = int(date[-1]) - 1
	yesterday = date[:-1] + str(prevDate)

	if yesterday in currHistoryObject: #there is an entry for yesterday
		recentFoods.append(currHistoryObject[yesterday]['Breakfast'].keys())
		recentFoods.append(currHistoryObject[yesterday]['Lunch'].keys())
		recentFoods.append(currHistoryObject[yesterday]['Dinner'].keys())
		recentFoods.append(currHistoryObject[yesterday]['Snacks'].keys())

	print ('recent foods: ', recentFoods)
	return recentFoods

"""
Function: get_important_macros

Fetches the important nutrients from a food's nutritional profile.

Arguments:
food_dict (object) : dictionary from Mongo with a food's nutrition values
nutrients (list) : list of all nutrient keys that are important

Returns:
(list) : list of the important nutrients
"""


def get_important_macros(
    food_dict, nutrients=["Protein (g)", "Fat (g)", "Carbohydrates (g)", "Calories"]
):
    return [food_dict[nutrient] for nutrient in nutrients]
