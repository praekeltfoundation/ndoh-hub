from csv import DictReader

# AND (fr.session_id is null or fr.parent_uuid is null)
# They're not linked to anything and the golang task just updates them.
FILE = "expired_runs4.csv"

input_file = DictReader(open(FILE))

run_ids = []
session_ids = []
for row in input_file:
    run_ids.append(row["run_id"])

    if row["session_id"]:
        session_ids.append(row["session_id"])


print(len(run_ids))
print(len(session_ids))

print(
    f"""UPDATE
		flows_flowsession s
	SET
		timeout_on = NULL,
		ended_on = NOW(),
		status = 'X'
	WHERE
		id = ANY(ARRAY[{",".join(session_ids)}])
"""
)

# print(f"""UPDATE
# 		flows_flowrun fr
# 	SET
# 		is_active = FALSE,
# 		exited_on = NOW(),
# 		exit_type = 'E',
# 		status = 'E',
# 		modified_on = NOW()
# 	WHERE
# 		id = ANY(ARRAY[{",".join(run_ids)}])
# """)

"""
UPDATE
flows_flowrun fr
SET
is_active = FALSE,
exited_on = NOW(),
exit_type = 'E',
status = 'E',
modified_on = NOW()
WHERE
id = ANY(ARRAY[80689]);

UPDATE
flows_flowsession s
SET
timeout_on = NULL,
ended_on = NOW(),
status = 'X'
WHERE
id = ANY(ARRAY[26641])
"""
