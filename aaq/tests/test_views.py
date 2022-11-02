import responses
from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework import status


from .helpers import FakeAaqCoreApi

############  TEST CORE API  ############


# class CoreInboundCheckTests(APITestCase):
#    def PostInboundCheckTest(self):
#        """
#        Check that the format of the response is as expected
#        """
#        # POST /inbound/check
#
#        mock_payload = {"text_to_match": "I am pregnant and out of breath"}
#
#        mock_response = {
#            "top_responses": [
#                [
#                    "21",
#                    "Feeling short of breath in pregnancy",
#                    "*Yes, pregnancy can affect your breathing*\r\n\r\nChanges in breathing during pregnancy are common. In the second trimester, your *growing uterus* 🤰🏽 takes up more space. This puts pressure on your diaphragm, the muscle below your lungs – so breathing may become difficult.\r\n\r\nYou may also experience shortness of breath if you: \r\n- put on a lot of weight during pregnancy\r\n- have a lot of amniotic fluid \r\n- are carrying your baby high, or carrying multiple babies\r\n- have anemia or asthma \r\n\r\nTowards the end of the third trimester, baby's larger size pushes the uterus into the diaphragm, pressing on your lungs.\r\n\r\n*What to do*\r\n- When feeling breathless, take things slowly 🧘🏽‍♀️\r\n- Sit upright to give your lungs space🧎🏽‍♀️\r\n- Stand straight, arms above your head, taking deep breaths  🌬️\r\n- Sleep propped up on your left side 🛌🏽\r\n- Do light exercise like walking or swimming 🏊🏽‍♀️\r\n- Relax and be still whenever you can 💆🏽‍♀️",
#                ],
#                [
#                    "26",
#                    "Fainting in pregnancy",
#                    "*Fainting could mean anemia – visit the clinic to find out*\r\n\r\nSometimes a lack of Iron in your blood (anemia) can cause dizziness 🥴 and fainting. If you faint please go to the clinic. A simple blood test can confirm if you are anemic.\r\n\r\n*What to do*\r\n- Ask a nurse about taking iron pills 💊\r\n- Prevent fainting by getting up slowly after sitting or lying – especially getting out of a bath 🛀🏽\r\n- If you feel dizzy or light-headed, lie down and put your feet up so you don't fall down. Alert the person next to you that you are not feeling well 🥴\r\n\r\n*Reasons to go to the clinic* 🏥\r\n- If you often feel dizzy or light-headed\r\n- If you have shortness of breath and heart palpitations together with feeling light-headed",
#                ],
#                [
#                    "114",
#                    "Bleeding in pregnancy",
#                    "*Bleeding during pregnancy*\r\n \r\n*Early pregnancy (months 1-3)*\r\nLight bleeding that doesn't last long is common, especially in the early weeks of pregnancy. It is nothing to worry about. There are many things that could cause bleeding at this stage, including sex, infection or changes in your body. \r\n \r\nNote how much bleeding there is and what it looks like. Mention any bleeding to your healthcare worker.\r\n \r\nGo to the clinic if you also have: 🏥\r\n• cramps in your lower body \r\n• severe nausea and vomiting\r\n \r\n*Later pregnancy (months 4-9)*\r\nGo to the clinic if you have any bleeding (light or heavy) in your 2nd or 3rd trimester.\r\n \r\nWear a pad to track how much you are bleeding. Notice what the bleeding looks like.\r\n \r\nThere are many things that could cause bleeding in later pregnancy, including pre-term labour.\r\n \r\nGet immediate help if you have: ❗\r\n• Severe pain or intense cramps low down\r\n• Severe bleeding\r\n• Discharge from the vagina that contains tissue\r\n• Dizziness or fainting\r\n• A fever",
#                ],
#                [
#                    "111",
#                    "Sleep in pregnancy",
#                    "*Get good sleep during pregnancy*\r\n\r\nGood sleep is important for your health. 😴 You need 7 to 8 hours each night. Sleep keeps your mood steady, helps you to think clearly and make good decisions and prevents sickness.\r\n\r\nSleep problems won't harm you or baby, but it can make life feel more difficult. In the first 12 weeks of pregnancy, you may feel more tired than usual. As your pregnancy progresses, it may be more difficult to sleep comfortably with a larger belly. 🤰🏽\r\n\r\n*What to do*\r\n- Go to bed early ⏰,\r\n- Avoid sleeping on your back after 20 weeks of pregnancy as it may increase the risk of stillbirth. Sleep on your side 🛌🏽 (ideally the left side) – it's more comfortable and improves blood flow, increasing the nutrients that reach your baby, \r\n- If you are heavily pregnant, place a pillow between your bent legs and knees for a more comfortable position – or you could also place a pillow below your belly and behind your back,\r\n- Don't drink alcohol or smoke cigarettes 🚭, this can disturb your sleep and harm baby, \r\n- Avoid screens 📵 (including your phone) for an hour before going to bed.\r\n\r\n*Reasons to go to the clinic* 🏥\r\nBeing unable to sleep could be a sign of depression or anxiety. This is nothing to be ashamed of. If you feel sad or anxious for more than 2 weeks, please visit the clinic to get advice from the nurse/midwife.",
#                ],
#                [
#                    "150",
#                    "Breast pain",
#                    "*Sometimes breast pain needs to be checked at the clinic*\r\n\r\nYour breasts will produce milk as long as baby demands it. But sometimes, breasts need care of their own. \r\n\r\n*Cracked nipples*\r\nThis is caused by incorrect latching (how baby grips the breast to feed). A good latch promotes milk flow and limits nipple pain for the mom. A poor latch means baby doesn't get enough milk – and can quickly lead to sore and cracked nipples. 😕\r\n\r\nBaby should have his mouth around most of the dark area of your nipple. If you see his jaw moving up and down as he feeds, you know he has latched well. \r\n\r\nUse nipple cream 🧴 for cracked nipples. If you are HIV positive, don't feed baby on the affected breast. \r\n\r\n*Breast engorgement*\r\nBreast engorgement is when your breasts are too full, feeling hard, tight and painful. This happens if baby hasn't fed for a while. Let him feed – or express milk to relieve the pressure and prevent mastitis, a painful breast infection 🦠 that needs medical care.\r\n\r\n*Blocked milk ducts*\r\nIf a milk-making gland in your breast isn't emptied during a feed 🤱🏽, it can lead to a blocked duct. You may feel a small, tender lump in your breast. During feeding, place your baby with her chin pointing towards the lump so he can feed from that part of the breast. Apply a warm compress on your breast for the pain. Avoid wearing tight clothes or bras.\r\n\r\n*Thrush*\r\nIf you have pain in both breasts and it lasts for up to an hour after a feed, you may have developed thrush. Thrush is a fungal infection that affects you and your baby. If you have thrush please go to the clinic to get treatment for both you and baby.\r\n\r\n*Reasons to go to the clinic* 🏥\r\nFor mastitis or cracked nipples, please go to the clinic for treatment.",
#                ],
#            ],
#            "feedback_secret_key": "4jCut//cRtokjKyMRVadOBDdluU56z51AsKUhsudI7A=",
#            "inbound_secret_key": "YF9ahzOThUpYtEB960z3v7XpBvy9gJ5Ui3nW43lTJgo=",
#            "inbound_id": "1766",
#            "next_page_url": "/inbound/1766/2?inbound_secret_key=YF9ahzOThUpYtEB960z3v7XpBvy9gJ5Ui3nW43lTJgo%3D",
#        }
#
#        self.assertTrue(True)
#
#    def GetPaginatedResponseTest(self):
#        # GET /inbound/<inbound_id>/<page_id>
#        # request https://mc-aaq-core-prd.ndoh-k8s.prd-p6t.org/inbound/270/2?inbound_secret_key=JkG0h6X5zLuirwB7l3739MVQ3CQbroR5yBI5eCOJgg8%3D
#
#        mock_response = {
#            "top_responses": [
#                [
#                    "106",
#                    "Breast changes in pregnancy",
#                    "*Expect breast changes during pregnancy*\r\n\r\nPregnancy brings many body changes – like changes to the shape, size and appearance of your breasts. \r\n\r\n*First trimester (months 1 to 3)* \r\n- Your breasts grow larger, \r\n- They may become sore or tender, \r\n- You may notice veins that are more blue and visible, \r\n- Your areola (the ring around the nipple) becomes darker or more sensitive. \r\n\r\nAs pregnancy progresses, your breasts keep changing. A chemical in your body called prolactin increases your breast size and starts milk production.\r\n\r\n*Second trimester (months 4 to 6)*\r\n- Your milk ducts develop and you may need a larger bra size (or two) to be comfortable, \r\n- Colostrum is the first type of breast milk your body makes. You may see this leaking into your bra. It is thicker and stickier than breast milk and very healthy for your baby. \r\n\r\n*Third trimester (months 7 to 9)*\r\n- Your breasts become heavier \r\n- Your areola and nipples may grow darker \r\n- Itchiness or dryness are normal because your skin has to stretch\r\n- If you develop stretch marks, protect your skin with a moisturising cream.\r\n\r\n*Ask at the clinic* 🏥\r\nIf you have questions or concerns about your breast shape or size, or other changes to your breasts, please visit the clinic to ask the nurse/midwife. ",
#                ],
#                [
#                    "19",
#                    "Nosebleeds in pregnancy",
#                    "*Don't worry about nosebleeds – unless you bleed heavily*\r\n\r\nNosebleeds 🤧 are common during pregnancy. There is no need to worry unless you lose a lot of blood. Nosebleeds are caused by pregnancy's hormonal changes. These hormonal changes also cause a stuffy or blocked nose during pregnancy. \r\n\r\n*What to do – during a nosebleed*\r\n- Lean forward from a sitting or standing position and breathe through your mouth, letting the blood drip into a basin or onto the ground, if outside. \r\n- Slow the blood flow by wrapping ice in a cloth and holding it against the bridge of your nose. \r\n\r\n*What to do – after a nosebleed*\r\n- Don't blow your nose or do heavy physical activity for half a day. \r\n\r\n*Reasons to go to the clinic 🏥*\r\n- If the bleeding🩸 does not stop, visit the clinic as soon as you can. \r\n- Visit the clinic if you have heart palpitations 💓 and shortness of breath (anemia). ",
#                ],
#                [
#                    "127",
#                    "Baby's growth - 9 to 12 months",
#                    "*Baby development – 9 to 12 months*\r\n\r\nYour baby starts to walk around using the furniture for support and can crawl well on her hands and knees. She will start to pick up toys 🧸  while in a standing position. Some babies will take a first few steps 👣, but for others this may be a few months away.\r\n\r\nPointing 👆🏽, nodding and waving 👋🏽 become part of baby's communication skills. She will start to speak using her first few words. By 12 months, your baby will be getting better at using her hands and fingers. She can hold a spoon 🥄 and will try to feed herself. Encourage baby to drink from a cup.",
#                ],
#                [
#                    "2",
#                    "Backache in pregnancy",
#                    "*Ways to manage back pain during pregnancy*\r\n\r\nPain or aching 💢 in the back is common during pregnancy. Throughout your pregnancy the hormone relaxin is released. This hormone relaxes the tissue that holds your bones in place in the pelvic area. This allows your baby to pass through you birth canal easier during delivery. These changes together with the added weight of your womb can cause discomfort 😓 during the third trimester. \r\n\r\n*What to do*\r\n- Place a hot water bottle 🌡️ or ice pack 🧊 on the painful area. \r\n- When you sit, use a chair with good back support 🪑, and sit with both feet on the floor. \r\n- Get regular exercise🚶🏽‍♀️and stretch afterwards. \r\n- Wear low-heeled 👢(but not flat ) shoes with good arch support. \r\n- To sleep better 😴, lie on your side and place a pillow between your legs, with the top leg on the pillow. \r\n\r\nIf the pain doesn't go away or you have other symptoms, visit the clinic.\r\n\r\nTap the link below for:\r\n*More info about Relaxin:\r\nhttps://www.yourhormones.info/hormones/relaxin/",
#                ],
#                [
#                    "116",
#                    "Bleeding after birth",
#                    "*Bleeding after birth*\r\n\r\n*It's normal to bleed after the birth🩸*. Your body is cleaning out your womb. During the first few days after birth, bleeding is like a heavy period. The bleeding then slows down. First it turns brown like old blood, then spotting (irregular bleeding) follows. This may continue for 6 weeks after birth. \r\n\r\n*Breastfeeding* 🤱🏽 your baby will help to shrink your womb and reduce bleeding. Make sure you have plenty of pads for the first few days when bleeding can be heavy. \r\n\r\n*Reasons to go to the clinic or hospital* 🏥\r\n- If the bleeding becomes lumpy/clotted or you bleed through 2 maternity pads in 1 hour, \r\n- If the blood becomes smelly, \r\n- If you develop a fever.",
#                ],
#            ],
#            "feedback_secret_key": "YQuOT6o7H+kfaePJBjc1sqXbjqhoble6Ky1iCcfAO4U=",
#            "inbound_secret_key": "JkG0h6X5zLuirwB7l3739MVQ3CQbroR5yBI5eCOJgg8=",
#            "inbound_id": "270",
#            "next_page_url": "/inbound/270/3?inbound_secret_key=JkG0h6X5zLuirwB7l3739MVQ3CQbroR5yBI5eCOJgg8%3D",
#            "prev_page_url": "/inbound/270/1?inbound_secret_key=JkG0h6X5zLuirwB7l3739MVQ3CQbroR5yBI5eCOJgg8%3D",
#        }
#
#        self.assertTrue(True)
#
#
# class AddFeedbackTests(APITestCase):
#    # url = reverse("aaq-add-feedback")
#
#    @responses.activate
#    def test_add_feedback_task(self):
#        """
#        Not sure if we can test tasks?
#        """
#
#        # PUT https://mc-aaq-core-prd.ndoh-k8s.prd-p6t.org/inbound/feedback
#
#        mock_payload = {
#            "feedback_secret_key": "Uh07rL7+CIO9mfDADXFGSFlkREllAP6ffeOoBfNMwxY=",
#            "inbound_id": "1752",
#            "feedback": {"feedback_type": "negative", "faq_id": "21"},
#        }
#        mock_response = "Success"
#        self.assertTrue(True)
#

############  TEST HUB APP API  ############


class GetFirstPageViewTests(APITestCase):
    url = reverse("aaq-get-first-page")

    def test_unauthenticated(self):
        """
        Unauthenticated users cannot access the API
        """
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # TODO: Test how we handle errors from aaq core?

    @responses.activate
    def test_get_first_page_view(self):
        """
        Check that we get 5 faqs returned with 1st page of inbound check
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        fakeCoreApi = FakeAaqCoreApi()
        responses.add_callback(
            responses.POST,
            "http://aaqcore/inbound/check",
            callback=fakeCoreApi.post_inbound_check,
            content_type="application/json",
        )

        payload = {"text_to_match": "I am pregnant and out of breath"}

        response = self.client.post(self.url, data=payload)
        print(response)
        print(response.json())
        assert response.json() == {
            "message": "*1* - short of breath\n*2* - Fainting in pregnancy\n*3* - Bleeding in pregnancy\n*4* - Sleep in pregnancy\n*5* - Breast pain",
            "body": {
                "1": {"text": "*Yes, pregnancy can affect your breathing ", "id": "21"},
                "2": {
                    "text": "*Fainting could mean anemia – visit the clinic to find out",
                    "id": "26",
                },
                "3": {
                    "text": "*Bleeding during pregnancy*\r\n \r\n*Early pregnancy ",
                    "id": "114",
                },
                "4": {
                    "text": "*Get good sleep during pregnancy*\r\n\r\nGood sleep is good",
                    "id": "111",
                },
                "5": {
                    "text": "*Sometimes breast pain needs to be checked at the clinic",
                    "id": "150",
                },
            },
            "next_page_url": "/inbound/iii/ppp?inbound_secret_key=zzz",
            "feedback_secret_key": "xxx",
            "inbound_secret_key": "yyy",
            "inbound_id": "iii",
        }
        


# class GetSecondPageViewTests(APITestCase):
#    url = reverse("aaq-get-second-page", kwargs={"inbound_id": 270, "page_id": 2})
#
#    @responses.activate
#    def test_get_second_page_view(self):
#        """
#        Check we can get the second page of a given inbound check, with another 5 faqs
#        """
#
#        self.assertTrue(True)
#
#
# class AddFeedbackViewTests(APITestCase):
#    url = reverse("aaq-add-feedback")
#
#    @responses.activate
#    def test_add_feedback_view(self):
#        """
#        Check that we can successfully hand off the task to celery
#        """
#
#        self.assertTrue(True)
#
