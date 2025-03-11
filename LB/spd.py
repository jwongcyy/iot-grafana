import numpy as np
import matplotlib.pyplot as plt

# Constants
h = 6.626e-34  # Planck's constant in J s
c = 3.00e8     # Speed of light in m/s

# Example SPDs (normalized)
def deep_red_spd(lambda_val):
    return np.exp(-((lambda_val - 660) / 10)**2)

def blue_spd(lambda_val):
    return np.exp(-((lambda_val - 450) / 10)**2)

def cool_white_spd(lambda_val):
    return 0.5 * np.exp(-((lambda_val - 450) / 10)**2) + 0.5 * np.exp(-((lambda_val - 550) / 10)**2)

def warm_white_spd(lambda_val):
    return np.exp(-((lambda_val - 600) / 10)**2)

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

# Example SPDs (absolute)
def deep_red_spd(lambda_val, power=10):  # W/m²
    return power * np.exp(-((lambda_val - 660) / 10)**2)

def blue_spd(lambda_val, power=5):  # W/m²
    return power * np.exp(-((lambda_val - 450) / 10)**2)

def cool_white_spd(lambda_val, power=15):  # W/m²
    return power * (0.5 * np.exp(-((lambda_val - 450) / 10)**2) + 0.5 * np.exp(-((lambda_val - 550) / 10)**2))

def warm_white_spd(lambda_val, power=12):  # W/m²
    return power * np.exp(-((lambda_val - 600) / 10)**2)

# Calculate combined SPD
combined_spd_abs = (deep_red_spd(lambda_range) + 
                    2 * blue_spd(lambda_range) + 
                    cool_white_spd(lambda_range) + 
                    warm_white_spd(lambda_range))

# Plot combined SPD
plt.plot(lambda_range, combined_spd_abs)
plt.xlabel('Wavelength (nm)')
plt.ylabel('Spectral Power (W/m²/nm)')
plt.title('Combined SPD in W/m²/nm')
plt.show()