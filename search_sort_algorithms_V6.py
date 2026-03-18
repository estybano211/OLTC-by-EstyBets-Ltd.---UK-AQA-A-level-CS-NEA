def linear_search(array, key, value):
    """
    Performs a linear search through a list of dictionaries.
    Checks every element from a starting index 0 until the target is found.
    Time complexity: O(n).

    Arg:
        array (list): A list of dictionaries to search.
        key (str): The dictionary key to inspect.
        value : The value to search for.

    Returns:
        int: Index of the first matching element, or -1 if not found.
    """
    for index in range(len(array)):
        if array[index].get(key) == value:
            return index
    return -1


def bubble_sort(array, key, reverse):
    """
    Sorts a list of dictionaries by a given key using bubble sort.
    Compares adjacent pairs and swaps if out of order.
    Time complexity: O(n^2)

    Args:
        array (list): List of dictionaries to sort.
        key (str): The dictionary key to sort by.
        reverse (bool): True for descending, False for ascending.

    Returns:
        list: A new sorted list.
    """
    array = array.copy()
    array_length = len(array)
    for pass_num in range(array_length - 1):
        swapped = False
        for index in range(
            array_length - 1 - pass_num
        ):  # Last 'pass_num' elements are already sorted
            value_a = array[index].get(key)
            value_b = array[index + 1].get(key)
            if (reverse and value_a < value_b) or (
                not reverse and value_a > value_b
            ):  # Compare based on sort order
                array[index], array[index + 1] = array[index + 1], array[index]
                swapped = True
        if not swapped:  # No swaps means the array is already sorted
            break
    return array


def binary_search_by_id(array, target_id):
    """
    Binary search on a list of dictionaries sorted ascending by 'user_id'.
    Time complexity: O(log n). List must be sorted first.

    Args:
        array (list): List of dictionaries sorted by 'user_id' ascending.
        target_id (int): The user_id to find.

    Returns:
        int: Index of the matching element, or -1 if not found.
    """
    low, high = 0, len(array) - 1
    while low <= high:
        mid = (low + high) // 2
        mid_id = array[mid].get("user_id", -1)
        if mid_id == target_id:
            return mid  # Target founf
        elif mid_id < target_id:
            low = mid + 1  # Target is in the upper half.
        else:
            high = mid - 1  # Target is in the lower half.
    return -1
