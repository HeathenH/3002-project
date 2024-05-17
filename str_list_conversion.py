import ast

def listToString(l):
    str1 = ""
    openCount = 0
    closeCount = 0
    for sublist in l:
        substr = str(sublist)
        substr = substr.replace("[[", ":")
        substr = substr.replace("]]", ":")

        substr = substr.replace("]", ":")
        substr = substr.replace("[", ":")
        str1 += substr
    str1 = str1.replace("::", ":")

    return str1

def stringToList(s):
    return s.split(":")
    

journey = [["odyssey", 4001, "Elizabeth Quay"], ["Warwick", "Morley", "Mirrabooka"], [4001, 2002, 3003], ["06:02,busC_I,stopC,06:10,TerminalI", "09:29,busI_J,stopI,09:45,JunctionJ", "10:12,busJ_H,stopJ,10:41,StationH"]]
print("\n ORIGINAL JOURNEY\n", journey, "\n")

journey_data_str = '|'.join([str(item) for item in journey])
print("\n STRING JOURNEY\n", journey_data_str, "\n")

# # journey_data_list = journey_data_str.split("|")
# print(journey_data_list)

# journey_data_full_list = []

# for ele in journey_data_list:
#     print(ele)
#     print(type(ele))
#     cleaned_ele1 = ele.replace("[","")
#     cleaned_ele2 = cleaned_ele1.replace("]","")
#     cleaned_ele3 = cleaned_ele2.replace("'","")
#     print(cleaned_ele3)
#     sublist = cleaned_ele3.split(",")
#     print(sublist)
#     print(type(sublist))

#     journey_data_full_list.append(sublist)

# print(journey_data_full_list)

# journey_data_list_final =[]
# for list in journey_data_full_list:
#     for ele in list:
#         elem = ele.strip()
# print(journey_data_full_list)


# print("\nMY STUFF\n")
# journey_str = listToString(journey)
# print("journey str: ", journey_str)

# journey_listified = stringToList(journey_str)
# print("journey list: ", journey_listified)
# for list in journey_listified:
#     print(list)

# print("\nNEW ATTEMPT\n")


# Split the string by '|'
split_strings = journey_data_str.split('|')
print("split_strings\n", split_strings)
# Convert each split string back to its list format
journey_listified = [ast.literal_eval(item) for item in split_strings]

print("\n LIST JOURNEY\n", journey_listified, "\n")

# station_data_string = "WARWICK" + "," + "4002" + "," + "station_port"
# print(station_data_string)

# station_data_list = station_data_string.split(",")
# print(station_data_list)

