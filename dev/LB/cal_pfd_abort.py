import pandas as pd
import numpy as np
import sys  # For exiting the program

def calculate_pfd(file_path, factor=0.00000836):
    """
    Calculate PFD (Photosynthetic Photon Flux Density) for various wavelength ranges
    and report the nm range, nm_min, nm_max, nm_delta, and check the decimal places of si.
    Abort if nm_delta is not 1.

    Parameters:
        file_path (str): Path to the CSV file containing 'nm' and 'si' columns.
        factor (float): Factor to multiply the summation of nm * si. Default is 0.00000836.

    Returns:
        dict: A dictionary containing PFD values for the entire range, PAR (400-700 nm),
              Red (600-699 nm), Green (500-599 nm), Blue (400-499 nm), Far Red (700-799 nm),
              nm_range, nm_min, nm_max, nm_delta, and si_decimal_places.
    """
    # Load the data from the CSV file
    data = pd.read_csv(file_path)

    # Calculate the range, min, and max of 'nm' values
    nm_min = data['nm'].min()
    nm_max = data['nm'].max()
    nm_range = nm_max - nm_min

    # Calculate the delta between consecutive 'nm' values
    nm_delta = data['nm'].diff().mean()  # Assume constant delta and take the mean

    # Abort if nm_delta is not 1
    if not np.isclose(nm_delta, 1.0, atol=1e-5):  # Allow for small floating-point errors
        print(f"Error: nm_delta is {nm_delta}, but it must be 1. Aborting.")
        sys.exit(1)  # Exit the program with a non-zero status code

    # Check the decimal places of 'si' values
    def count_decimal_places(x):
        """
        Count the number of decimal places in a floating-point number.
        """
        if isinstance(x, float):
            # Convert to string and split into integer and decimal parts
            parts = str(x).split('.')
            if len(parts) == 2:
                return len(parts[1])
        return 0

    # Apply the function to count decimal places for each 'si' value
    si_decimal_places = data['si'].apply(count_decimal_places)

    # # Check if all 'si' values have the same number of decimal places
    # unique_decimal_places = si_decimal_places.unique()
    # if len(unique_decimal_places) == 1:
    #     print(f"All 'si' values have {unique_decimal_places[0]} decimal places.")
    # else:
    #     print(f"'si' values have varying decimal places: {unique_decimal_places}")

    # Calculate the product of 'nm' and 'si'
    data['nm_si'] = data['nm'] * data['si']

    # Define wavelength ranges
    ranges = {
        'total': (nm_min, nm_max),
        'par': (400, 700),
        'r': (600, 699),
        'g': (500, 599),
        'b': (400, 499),
        'fr': (700, 799)
    }

    # Calculate PFD for each range
    pfd_results = {}
    for key, (start, end) in ranges.items():
        sum_range = data[(data['nm'] >= start) & (data['nm'] <= end)]['nm_si'].sum()
        pfd_results[f'pfd_{key}'] = round(factor * sum_range, si_decimal_places.min())

    # Add nm_range, nm_min, nm_max, nm_delta, and si_decimal_places to the results
    pfd_results['nm_range'] = nm_range
    pfd_results['nm_min'] = nm_min
    pfd_results['nm_max'] = nm_max
    pfd_results['nm_delta'] = int(nm_delta)
    return pfd_results

# Example usage
if __name__ == "__main__":
    # Path to the CSV file
    file_path = 'source.csv'

    # Call the function
    pfd_results = calculate_pfd(file_path)

    # Print the results
    print(f"Spectural range: {pfd_results['nm_min']} - {pfd_results['nm_max']} nm; Wavelength step: {pfd_results['nm_delta']} nm")
    print(f"PFD: {pfd_results['pfd_total']}")
    print(f"PFD-R: {pfd_results['pfd_r']} | PFD-G: {pfd_results['pfd_g']} | PFD-B: {pfd_results['pfd_b']} | PFD-FR: {pfd_results['pfd_fr']}")
    print(f"PFD-PAR: {pfd_results['pfd_par']}")