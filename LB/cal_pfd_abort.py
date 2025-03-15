import pandas as pd
import numpy as np
import sys  # For exiting the program

def calculate_pfd(file_path, factor=0.00000836):

    # load csv
    data = pd.read_csv(file_path)

    nm_delta = data['nm'].diff().mean()
    nm_min = data['nm'].min()
    nm_max = data['nm'].max()

    # Abort if nm_delta is not 1
    if not np.isclose(nm_delta, 1.0, atol=1e-5):  # Allow for small floating-point errors
        print(f"Error: nm_delta is {nm_delta}, but it must be 1. Aborting.")
        sys.exit(1)  # Exit the program with a non-zero status code


    # calculate contribution (nm * si)
    data['nm_si'] = data['nm'] * data['si']

    # define RBG, PAR
    ranges = {
        'total': (nm_min, nm_max),
        'par': (400, 700),
        'r': (600, 699),
        'g': (500, 599),
        'b': (400, 499),
        'fr': (700, 799)
    }

    # calculate pfd
    pfd_out = {}
    for key, (start, end) in ranges.items():
        sum_range = data[(data['nm'] >= start) & (data['nm'] <= end)]['nm_si'].sum()
        pfd_out[f'pfd_{key}'] = round(factor * sum_range, 3)

    # include nm_delta, nm_min, and nm_max
    pfd_out['nm_delta'] = int(nm_delta)
    pfd_out['nm_min'] = nm_min
    pfd_out['nm_max'] = nm_max

    return pfd_out

if __name__ == "__main__":

    # path to csv
    file_path = 'source.csv'

    # run function
    pfd_out = calculate_pfd(file_path)

    # output
    print(f"Spectural range: {pfd_out['nm_min']} - {pfd_out['nm_max']} nm; Wavelength step: {pfd_out['nm_delta']} nm")
    print(f"PFD: {pfd_out['pfd_total']}")
    print(f"PFD-R: {pfd_out['pfd_r']} | PFD-G: {pfd_out['pfd_g']} | PFD-B: {pfd_out['pfd_b']} | PFD-FR: {pfd_out['pfd_fr']}")
    print(f"PFD-PAR: {pfd_out['pfd_par']}")