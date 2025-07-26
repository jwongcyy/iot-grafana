import numpy as np
import matplotlib.pyplot as plt

# Constants
h = 6.626e-34  # Planck's constant in J s
c = 3.00e8     # Speed of light in m/s

deep_red_nm = 660
blue_nm = 450
# blue_nm1 = 430
# blue_nm2 = 480
cool_white_nm1 = 450
cool_white_nm2 = 550
warm_white_nm = 600

def calculate_total_wattage():
    # Define the wattage of each LED type - 5050 LEDs
    deep_red_wattage = 0.5
    blue_wattage = 0.5
    cool_white_wattage = 0.5
    warm_white_wattage = 0.5

    # # Define the wattage of each LED type - 5050 LEDs
    # deep_red_wattage = 10
    # blue_wattage = 5
    # cool_white_wattage = 15
    # warm_white_wattage = 12

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

# Wattage of LED setup
total_wattage = calculate_total_wattage()
print(f"Total wattage with safety margin: {total_wattage} W")

# Example SPDs (normalized)
def deep_red_spd(lambda_val):
    return np.exp(-((lambda_val - deep_red_nm) / 10)**2)

def blue_spd(lambda_val):
    return np.exp(-((lambda_val - blue_nm) / 10)**2)

def cool_white_spd(lambda_val):
    return 0.5 * np.exp(-((lambda_val - cool_white_nm1) / 10)**2) + 0.5 * np.exp(-((lambda_val - cool_white_nm2) / 10)**2)

def warm_white_spd(lambda_val):
    return np.exp(-((lambda_val - warm_white_nm) / 10)**2)

# Wavelength range
lambda_range = np.linspace(380, 780, 400)

# Calculate combined SPD
combined_spd = (deep_red_spd(lambda_range) + 
                2 * blue_spd(lambda_range) + 
                cool_white_spd(lambda_range) + 
                warm_white_spd(lambda_range))

# Normalize combined SPD
combined_spd /= np.sum(combined_spd)

# Calculate PPFD
ppfd = np.sum(combined_spd[(lambda_range >= 400) & (lambda_range <= 700)] * 
              (lambda_range[(lambda_range >= 400) & (lambda_range <= 700)] * 1e-9) / 
              (h * c)) * (1 / (4.57e-6)) * (400 / len(lambda_range))

# Print PPFD
print(f"PPFD: {ppfd} μmol/m²s")

# Plot combined SPD
plt.plot(lambda_range, combined_spd)
plt.xlabel('Wavelength (nm)')
plt.ylabel('Normalized Radiant Power')
plt.title('Combined SPD')
plt.show()