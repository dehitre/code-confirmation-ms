import requests
import json
import pytest
import random
import psycopg2
import allure_pytest
import allure



@pytest.fixture(scope="function")
def get_address():
    link = "http://confirmation-code-processor.pre.spb.play.dc/v1/codes"
    return link


@pytest.fixture(scope="function")
def get_phone():
    return int("7999" + str(random.randint(1000000, 9999999)))


@pytest.fixture(scope="function")
def get_user():
    return random.randint(100000, 999999)


@pytest.fixture(scope="function")
def use_by_phone_address():
    def _verification_address(code):
        link = "http://confirmation-code-processor.pre.spb.play.dc/v1/codes/" + code + "/check-phone-and-delete"
        return link
    return _verification_address


@pytest.fixture(scope="function")
def use_by_user_address():
    def _verification_address(code):
        link = "http://confirmation-code-processor.pre.spb.play.dc/v1/codes/" + code + "/user"
        return link
    return _verification_address


@allure.step("Change code creation time in db")
def change_time_of_code(code):
    query = "UPDATE confirmationcode set created_ts = now()-INTERVAL '30 minutes' where code='" + code + "'"

    conn = psycopg2.connect(host="pre-postgres-confirmationcodes-master.spb.play.dc", port="5433",
                            dbname="confirmationcodes", user="confirmationcodes", password="confirmationcodes")
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    cursor.close()
    conn.close()
    return True



@allure.step("Find code in db")
def check_code(code):
    query = "SELECT code FROM confirmationcode where code='" + code + "'"
    conn = psycopg2.connect(host="pre-postgres-confirmationcodes-master.spb.play.dc", port="5433",
                            dbname="confirmationcodes", user="confirmationcodes", password="confirmationcodes")
    cursor = conn.cursor()
    result = cursor.execute(query)
    conn.commit()
    cursor.close()
    conn.close()
    return result



@allure.title("Check creation and using confirmation code")
def test_code_confirmation(get_address, get_phone,use_by_phone_address):
    data = {"codeType": "CONFIRMATION", "phone": get_phone, "requestType": "BY_PHONE"}
    headers = {'Content-Type': 'application/json'}
    create_code_response = requests.post(get_address, headers=headers, data=json.dumps(data))
    code_length = len(create_code_response.json()["code"])
    code_ttl = create_code_response.json()["ttl"]
    code = create_code_response.json()["code"]
    assert create_code_response.status_code == 200
    assert code_length == 5
    assert code_ttl =="PT4H"
    use_code_response = requests.post(use_by_phone_address(code), headers=headers, data=json.dumps(data))
    assert use_code_response.status_code == 200
    code_in_db = check_code(code)
    assert code_in_db is None


@allure.title("Check creation and using registration code")
def test_create_code_registration(get_address, get_phone,use_by_phone_address):
    data = {"codeType": "REGISTRATION", "phone": get_phone, "requestType": "BY_PHONE"}
    headers = {'Content-Type': 'application/json'}
    create_code_response = requests.post(get_address, headers=headers, data=json.dumps(data))
    code_length = len(create_code_response.json()["code"])
    code_ttl = create_code_response.json()["ttl"]
    code = create_code_response.json()["code"]
    assert create_code_response.status_code == 200
    assert code_length == 5
    assert code_ttl =="PT30M"
    use_code_response = requests.post(use_by_phone_address(code), headers=headers, data=json.dumps(data))
    assert use_code_response.status_code == 200
    code_in_db = check_code(code)
    assert code_in_db is None


@allure.title("Check creation and using merge code")
def test_create_code_merge(get_address, get_user,use_by_user_address):
    data = {"codeType": "MERGE", "userId": get_user, "requestType": "BY_USER_ID"}
    headers = {'Content-Type': 'application/json'}
    create_code_response = requests.post(get_address, headers=headers, data=json.dumps(data))
    code_length = len(create_code_response.json()["code"])
    code_ttl = create_code_response.json()["ttl"]
    code = create_code_response.json()["code"]
    assert create_code_response.status_code == 200
    assert code_length == 5
    assert code_ttl =="PT30M"
    use_code_response = requests.post(use_by_user_address(code), headers=headers, data=json.dumps(data))
    assert use_code_response.status_code == 200
    assert use_code_response.json()["userId"] == data["userId"]
    code_in_db = check_code(code)
    assert code_in_db is None


@allure.title("Check wrong code for confirmation/registration codes")
def test_wrong_code_error_by_phone(use_by_phone_address, get_phone):
    data = {"codeType": "REGISTRATION", "phone": get_phone, "requestType": "BY_PHONE"}
    headers = {'Content-Type': 'application/json'}
    use_code_response = requests.post(use_by_phone_address("0000"), headers=headers, data=json.dumps(data))
    assert use_code_response.status_code == 400
    assert use_code_response.json()["message"] == "Confirmation code is incorrect"
    assert use_code_response.json()["errorCode"] == "INCORRECT_CODE"


@allure.title("Check expired code for confirmation/registration codes")
def test_expired_code_error_by_phone(get_address,use_by_phone_address, get_phone):
    data = {"codeType": "REGISTRATION", "phone": get_phone, "requestType": "BY_PHONE"}
    headers = {'Content-Type': 'application/json'}
    create_code_response = requests.post(get_address, headers=headers, data=json.dumps(data))
    code = create_code_response.json()["code"]
    change_time_of_code(code)
    use_code_response = requests.post(use_by_phone_address(code), headers=headers, data=json.dumps(data))
    assert use_code_response.status_code == 400
    assert use_code_response.json()["message"] == "Confirmation code expired"
    assert use_code_response.json()["errorCode"] == "CODE_EXPIRED"


@allure.title("Check wrong code for merge codes")
def test_wrong_code_error_by_user(get_user, use_by_user_address):
    data = {"codeType": "MERGE", "userId": get_user, "requestType": "BY_USER_ID"}
    headers = {'Content-Type': 'application/json'}
    use_code_response = requests.post(use_by_user_address("0000"), headers=headers, data=json.dumps(data))
    assert use_code_response.status_code == 400
    assert use_code_response.json()["message"] == "Confirmation code is incorrect"
    assert use_code_response.json()["errorCode"] == "INCORRECT_CODE"


@allure.title("Check expired code for merge codes")
def test_expired_code_error_by_user(get_address, get_user, use_by_user_address):
    data = {"codeType": "MERGE", "userId": get_user, "requestType": "BY_USER_ID"}
    headers = {'Content-Type': 'application/json'}
    create_code_response = requests.post(get_address, headers=headers, data=json.dumps(data))
    code = create_code_response.json()["code"]
    change_time_of_code(code)
    use_code_response = requests.post(use_by_user_address(code), headers=headers, data=json.dumps(data))
    assert use_code_response.status_code == 400
    assert use_code_response.json()["message"] == "Confirmation code expired"
    assert use_code_response.json()["errorCode"] == "CODE_EXPIRED"
