"""
tests.assistant_routing_corpus
================================

Realistic things the owner says to MIA, each paired with the Assistant
action that must be *offered* to the model for it (or INFO: answer from
help docs, no tools). The model can only call a tool it was offered, so
this is the deterministic half of MIA's conversational ability, testable
without a live model. tests/test_assistant_routing.py enforces it;
tests/live_model_check.py covers the model's half on real hardware.

Add a line here whenever you notice MIA miss something you said.
"""

from __future__ import annotations

INFO = "INFO"

CORPUS: list[tuple[str, str]] = [
    # ---- Assets & maintenance -------------------------------------------
    ("Start tracking my chainsaw", "add_maintenance_asset"),
    ("Add my Honda generator to maintenance", "add_maintenance_asset"),
    ("I just put 120 hours on the mower", "log_maintenance_reading"),
    ("Log 45,210 miles on the truck", "log_maintenance_reading"),
    ("Update the mileage on the truck to 46,000", "log_maintenance_reading"),
    ("I changed the oil in the truck today", "complete_maintenance_task"),
    ("Sharpened the mower blades this morning", "complete_maintenance_task"),
    ("What maintenance is due?", "list_maintenance_tasks"),
    ("Is anything overdue on the truck?", "list_maintenance_tasks"),
    ("Remind me to rotate the truck tires every 6 months", "add_maintenance_task"),
    ("My mower is a John Deere Z315E", "update_maintenance_asset"),
    ("The truck's serial number is 5FPYK3F79NB012345", "update_maintenance_asset"),
    ("Tell me about my mower", "get_maintenance_asset"),
    ("What do you know about the truck?", "get_maintenance_asset"),
    ("Note that the mower's deck belt is starting to fray", "add_asset_note"),
    ("What vehicles am I tracking?", "list_maintenance_assets"),
    # ---- Greenhouse & garden (Garden/Plant maintenance assets) ----------
    ("Add the tomato bed to the greenhouse", "add_maintenance_asset"),
    ("Start tracking my blueberry bushes in the garden", "add_maintenance_asset"),
    ("Remind me to water the tomatoes every 2 days", "add_maintenance_task"),
    ("I watered the tomatoes", "complete_maintenance_task"),
    ("I fertilized the peppers", "complete_maintenance_task"),
    ("The peppers are starting to flower", "add_asset_note"),
    ("What's due in the greenhouse?", "list_maintenance_tasks"),
    ("What plants am I tracking?", "list_maintenance_assets"),
    # ---- Bills, income, expenses, budget ---------------------------------
    ("I paid the electric bill", "mark_bill_paid"),
    ("Add my car insurance bill, $118 due on the 5th", "add_bill"),
    ("I spent $84 on groceries", "add_expense"),
    ("Log a $35 expense for mower blades", "add_expense"),
    ("How much have I spent this month?", "get_budget_summary"),
    ("I got paid today", "mark_income_received"),
    ("Got rent for the Maple duplex", "record_rental_income"),
    ("Set my grocery budget to $600 a month", "set_budget_target"),
    ("Are we on budget?", "get_financial_checkin"),
    # ---- Debts ---------------------------------------------------------------
    ("I owe $5,100 on my Capital One card at 27.49 percent", "add_debt"),
    ("Add my truck loan, $18,250 at 6.9 percent", "add_debt"),
    ("How much debt do I have?", "list_debts"),
    ("List my debts", "list_debts"),
    ("I paid $200 toward my Chase card", "record_debt_payment"),
    ("Made a $455 truck loan payment", "record_debt_payment"),
    ("Which debt should I pay off first?", "get_debt_payoff_plan"),
    ("What's my debt payoff plan?", "get_debt_payoff_plan"),
    # ---- Kitchen: recipes, meals -----------------------------------------
    ("Add a recipe for venison chili", "add_recipe"),
    ("Save my garden omelette recipe", "add_recipe"),
    ("What recipes do I have?", "list_recipes"),
    ("What can I make with what I have?", "suggest_recipes"),
    ("What can I cook tonight?", "suggest_recipes"),
    ("I made the venison chili tonight", "log_meal"),
    ("We had the garden omelette for breakfast", "log_meal"),
    # ---- Groceries ---------------------------------------------------------
    ("Add eggs and milk to the grocery list", "add_grocery_item"),
    ("Put coffee on the shopping list", "add_grocery_item"),
    ("What's on my grocery list?", "list_grocery_list"),
    ("I bought the eggs", "check_off_grocery_item"),
    ("Check off milk", "check_off_grocery_item"),
    ("Add what I need for the venison chili to the grocery list", "add_recipe_ingredients_to_grocery_list"),
    # ---- Pantry --------------------------------------------------------------
    ("I have 10 pounds of flour in the pantry", "add_pantry_item"),
    ("We're out of flour", "update_pantry_item"),
    ("What's in the pantry?", "list_pantry"),
    # ---- Electronics parts -------------------------------------------------
    ("Add 50 red LEDs to my parts", "add_component"),
    ("Do I have any 555 timers?", "list_components"),
    ("I used two 10k resistors", "adjust_component_quantity"),
    ("I bought 20 more 10k resistors", "adjust_component_quantity"),
    # ---- Fabrication materials -----------------------------------------------
    ("Add plywood to my materials", "add_material"),
    ("How much plywood do I have?", "list_materials"),
    ("I bought 4 more sheets of plywood", "adjust_material_quantity"),
    ("Plywood costs $42 a sheet now", "update_material"),
    # ---- Products & sales ------------------------------------------------------
    ("I made 5 more cutting boards", "adjust_product_stock"),
    ("I sold 2 cutting boards for $40 each", "record_sale"),
    ("What products do I have?", "list_products"),
    # ---- General inventory -----------------------------------------------------
    ("How many AA batteries do I have in inventory?", "list_inventory"),
    ("Add a tarp to inventory", "add_inventory_item"),
    # ---- Workout ---------------------------------------------------------------
    ("Log my workout: 3x10 squats at 185 and 3x8 bench at 155", "log_workout"),
    ("I did 3 sets of 10 deadlifts at 225", "log_workout"),
    ("How many workouts have I done this week?", "get_workout_summary"),
    ("What's my personal record on the squat?", "get_personal_record"),
    # ---- People & pets -----------------------------------------------------------
    ("Add my sister Megan, her birthday is June 12", "add_person"),
    ("Sarah's birthday is March 3", "update_person"),
    ("Sarah would love a new cast iron skillet", "update_person"),
    ("Gift ideas for Sarah?", "get_person"),
    ("Any birthdays coming up?", "list_upcoming_birthdays"),
    ("We adopted a beagle named Rosie", "add_pet"),
    ("Biscuit went to the vet for his shots today", "update_pet"),
    ("When was Biscuit's last vet visit?", "get_pet"),
    # ---- Household routines ------------------------------------------------------
    ("I did a load of laundry", "log_household_routine"),
    ("Did the dishes", "log_household_routine"),
    ("What chores are left today?", "list_household_routines"),
    ("Add a routine: vacuum twice a week", "add_household_routine"),
    # ---- Classroom -----------------------------------------------------------------
    ("Add a course on residential wiring under Electrical", "add_course"),
    ("I finished the lesson on circuit breakers", "complete_lesson"),
    ("Add to my notes for GFCI outlets: test them monthly", "add_lesson_notes"),
    ("What am I learning right now?", "get_learning_progress"),
    ("What's my next lesson?", "get_learning_progress"),
    # ---- Private journal (read back; needs the journal unlocked) -----------------
    ("What did I write in my journal about work?", "read_private_journal"),
    ("What's been on my mind lately?", "get_journal_themes"),
    ("What have I been writing about?", "get_journal_themes"),
    # ---- Your reasons ("Remember Why", core/assistant_why_actions.py) ------------
    ("The reason I work at the factory is to pay off my debt", "link_my_reason"),
    ("Paying off debt is so I can control my own time", "link_my_reason"),
    ("Show my why", "show_my_why"),
    ("What am I working toward?", "show_my_why"),
    ("I achieved my goal of paying off my debt", "mark_goal_achieved"),
    # ---- Homestead builds and tools (Finance #2) --------------------------------------
    ("I spent $240 on lumber for the greenhouse", "log_build_expense"),
    ("Spent 85 bucks on concrete for the fence posts", "log_build_expense"),
    ("I bought a DeWalt drill for $199 for the greenhouse", "record_tool_purchase"),
    ("I just bought a chainsaw for $329", "record_tool_purchase"),
    ("How much have I spent on the greenhouse?", "get_build_costs"),
    ("What has the mower cost me?", "get_tool_costs"),
    ("What's the mower's cost per hour?", "get_tool_costs"),
    ("Set a budget for the greenhouse of $5,000", "set_build_budget"),
    # ---- Business use of equipment (Finance #3) --------------------------------------
    ("I mowed the Maple duplex for 2 hours", "log_business_use"),
    ("Log 3 hours on the mower for the Johnson lawn job", "log_business_use"),
    ("How much of the mower can I write off this year?", "get_business_use"),
    ("What's the mower's business use percentage?", "get_business_use"),
    # ---- Textbook tutor ------------------------------------------------------------------
    ("What textbooks do I have?", "list_textbooks"),
    ("What does my textbook say about GFCI outlets?", "search_textbook"),
    ("Which page talks about grounding?", "search_textbook"),
    ("Make a course from my wiring textbook", "make_textbook_course"),
    # ---- Document inbox ------------------------------------------------------------------
    ("What's in my inbox?", "list_inbox"),
    ("Any new documents?", "list_inbox"),
    ("File it", "file_inbox_item"),
    ("File the Lowe's receipt under the greenhouse", "file_inbox_item"),
    ("File the mower manual without the tasks", "file_inbox_item"),
    ("Don't file the Amazon receipt, just dismiss it", "dismiss_inbox_item"),
    # ---- Sorting bank charges to businesses ---------------------------------------
    ("Which charges need a business?", "list_untagged_charges"),
    ("Any untagged bank charges?", "list_untagged_charges"),
    ("The Shell charge was for lawn care", "tag_charge"),
    ("The Walmart one was personal", "tag_charge"),
    # ---- When MIA speaks up (core/assistant_comm_actions.py) ------------------------
    ("What didn't you tell me today?", "get_held_back_messages"),
    ("Is there anything you held back?", "get_held_back_messages"),
    ("Only message me 3 times a day", "set_message_limit"),
    ("You can message me more", "set_message_limit"),
    # ---- Self-knowledge / how-to (answer from help docs, no tools) ------------
    ("How do I add a bill?", INFO),
    ("How do I track my mower?", INFO),
    ("How can I add a recipe?", INFO),
    ("Where do I see my debts?", INFO),
    ("Teach me how missions work", INFO),
    ("What can you do?", INFO),
    ("What does the Greenhouse module do?", INFO),
]


# Ordinary conversation that must NOT pull in any tools (an action-path
# turn loses MIA's warmth and help-doc grounding, and gives the model
# tools it might misuse). Known, accepted exceptions are documented in
# docs/ASSISTANT_AUDIT.md rather than listed here.
NO_TOOLS: list[str] = [
    "Good morning MIA",
    "Thanks, that's all",
    "I'm tired today",
    "Tell me a joke",
    "How was your day?",
    "I love gardening",
    "My brother is visiting this weekend",
    "The stock market is down today",
    "I need to log off for the night",
    "I'm starting to feel better",
    "I got the job!",
    "What's a good name for a dog?",
    "It costs too much to eat out",
    "Customer service was terrible",
    "Save my progress",
    "The plant down the road closed",
    "What's the capital of Kentucky?",
    "I had a great breakfast",
    "My dinner plans fell through",
    "I love to cook",
    # Long-standing live-model golden-set false-positive checks.
    "This shirt is made of a soft material",
    "What's a good way to budget my paycheck?",
    "That's a really useful property of this material",
    "I love my new job at the bakery",
    "Of course, that makes sense",
    "My neighbor's cat got out again",
    "I sat on a bench at the park",
    "I hate this. I want to go home.",
    "I'm tired of doing the same thing every day",
    "Work was awful today",
    "I'm saving up so I can buy a boat someday",
    "I love my books",
    "I checked my email this morning",
    "The filing cabinet is full",
]
