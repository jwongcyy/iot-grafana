def calculate_total_wattage():
    # Define the wattage of each LED type
    deep_red_wattage = 10
    blue_wattage = 5
    cool_white_wattage = 15
    warm_white_wattage = 12

    # Number of each LED type
    num_deep_red = 1
    num_blue = 2
    num_cool_white = 1
    num_warm_white = 1

    # Calculate total wattage
    total_wattage = (num_deep_red * deep_red_wattage) + \
                    (num_blue * blue_wattage) + \
                    (num_cool_white * cool_white_wattage) + \
                    (num_warm_white * warm_white_wattage)

    # Add a safety margin
    safety_margin = total_wattage * 0.10
    total_wattage_with_margin = total_wattage + safety_margin

    return total_wattage_with_margin

# Execute the function
total_wattage = calculate_total_wattage()
print(f"Total wattage with safety margin: {total_wattage} W")
