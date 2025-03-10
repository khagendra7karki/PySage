import json

def downloaded_files():
    code = './new-python-dataset/code.jsonl'
    ids ='./repo-id/ids.jsonl'

    with open(code, 'r') as c, open(ids, 'r') as i:
        
        set_c_only=set()
        set_i_only=set()
        
        list_c=[]  # list of repo_names in code file
        list_i=[]   # list of repo_names in ids file
        counter=0

        for line_c, line_i in zip(c, i):
            counter +=1

            
            in_c=line_c.split('"')[3]
            in_i=line_i.split('"')[3]

            # print(in_c, in_i)

            list_c.append(in_c)
            list_i.append(in_i)

            if counter % 10000 == 0:
                print(counter)
                set_c_only.update(list_c)
                set_i_only.update(list_i)

                set_c_only, set_i_only=set_c_only - set_i_only, set_i_only - set_c_only     # retain only those names that are only in code file
                # set_i_only=set_i_only - set_c_only     # retain only those names that are only in ids file

                list_c.clear()
                list_i.clear()

        # process the ids since it is longer and zips stops before finishing it
        for line_i in i:
            counter += 1
            in_i=line_i.split('"')[3]

            list_i.append(in_i)


        set_i_only.update(list_i)
        set_c_only.update(list_c)
    
        set_c_only, set_i_only=set_c_only - set_i_only, set_i_only - set_c_only     # retain only those names that are only in code file

        list_c.clear()
        list_i.clear()

        print(counter)

        return set_c_only, set_i_only
    

c, i = downloaded_files()

print(c, i)
# print(len(c), len(i))
# print(downloaded_files())




        