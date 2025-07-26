import math

def calculate_ppfd(ppf, radius):
    area = math.pi * radius**2
    ppfd = ppf / area
    return round(ppfd, 2)

# Example values
power_consumption = 15  # W
efficiency = 2  # μmol/J
radius = (150/2)/10/100  # m

# Calculate PPF
ppf = power_consumption * efficiency

# Calculate PPFD
ppfd = calculate_ppfd(ppf, radius)

print(f"PPFD: {ppfd} μmol/m²s")