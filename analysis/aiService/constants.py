OPENING_STATEMENT_DEFINITION = (
    "The OPENING includes the initial part of the interaction where"
    " the Sales Representative (REP) sets the context or purpose of the conversation "
    "with the Healthcare Professional (HCP)."
    " It often involves a greeting or acknowledgment of the HCP's time,"
    " followed by a brief overview of the discussion topic. "
    "The opening may also contain a 'permission to continue' question or statement,"
    " subtly seeking the HCP's consent to engage in the conversation."
    " The segment of the conversation where the REP introduces the purpose of the interaction, "
    "often seeking acknowledgement or permission to proceed with the discussion. "
    "It sets the stage for what is to be discussed.")

OPENING_STATEMENT_LEVEL = {
    "level_1": ["No purpose shared"],
    "level_2": [
      "Discussing, talking, debating are all level 2, unless a specific action; prescribing, using, introducing, changing are presented as well",
      "The purpose is to show, provide, share or discuss information",
      "The purpose is to find out or discuss information",
      "The purpose is to highlight a subject for discussion",
      "The purpose is delivered piecemeal throughout the interaction"
    ],
    "level_3": ["The purpose is an action. When the action is shared at the beginning of the interaction, it is a precise, unambiguous, action, concisely described to the HCP. Permission is NOT explicitly asked for at this point."],
    "level_4": ["The purpose is a shared action. When the action is shared at the beginning of the interaction, it is a precise, unambiguous, action, concisely described and agreed to the HCP. Permission is explicitly asked for at this point. e.g. Is that okay?"]
  }


QUESTIONING_STATEMENT_DEFINITON = (
    "The QUESTIONING phase involves the REP asking the HCP various questions related to the discussion topic."
    " These questions are aimed at gathering information to better understand the HCP's experiences,"
    " opinions, or practices regarding the subject matter. "
    "The questioning helps the REP tailor the conversation in a way that"
    " addresses the HCP's specific concerns or interests. "
    "A series of inquiries made by the REP to gain insights into the HCP's current practices,"
    " experiences, or opinions. These questions guide the flow of the conversation and "
    "help identify the HCP's needs or concerns.")

QUESTIONING_STATEMENT_LEVEL = {
    "level_1": ["Social interaction questions -These are questions that engage the HCP and create rapport, but do not explore job related specifics."],
    "level_2": [
      "Situational questions - These questions seek to understand the what’s happening now.",
      "How decisions are made now",
      "What people think now",
      "What is happening now",
      "Observations of what happens now",
      "Current thoughts & opinions",
      "Current situation",
      "Current prescribing",
      "Experiences",
      "Simple decision-making questions and clarification are also included here for convenience.",
      "Additionally, after presenting data or studies asking for HCP’s thoughts and opinions is included here."
    ],
    "level_3": [
      "Low return needs questions to uncover HCP needs - These questions uncover what I need to do to change the behaviour of the HCP, but are less productive and can damage rapport between the Rep and the HCP.",
      "Problem Questions – problems, issues, challenges – Is there a problem we can solve for the HCP",
      "Stop Questions – stop, barriers, obstacles – Are there barriers that need to be overcome",
      "Why Questions – Asking HCP’s to justify their behaviour – Do we understand the reasons why they behaviour the way they do, then we can present counter arguments"
    ],
    "level_4": [
      "High return needs questions to uncover HCP needs These questions uncover what I need to do to change the behaviour of the HCP, but are more productive and help build or maintain rapport between the Rep and the HCP.",
      "Improvement Questions – Improve, better, change – Is there a better solution the HCP wants",
      "Go Questions – Go, possibilities, opportunities – What are the positives that",
      "Past Decisions Questions – Asking HCP’s for the process they used",
      "Ideals Questions – perfect solution, blue sky thinking, imagination"
    ]
  }

PRESENTING_STATEMENT_DEFINITON = (
    "The PRESENTING phase is characterized by the REP sharing specific information, "
    "data, or scientific findings with the HCP. This can include details about a product, "
    "results from studies or trials, comparisons with other treatments, and guidelines."
    " The presentation is designed to inform, emphasize benefits, and "
    "address any efficacy or safety questions the HCP might have."
    " The portion of the dialogue where the REP provides "
    "detailed information about the product or treatment,"
    " often including data from studies, clinical trials, or guidelines."
    " This aims to inform and persuade based on evidence and scientific findings."
)

PRESENTING_STATEMENT_LEVEL = {
    "level_1": ["No scientific findings / information is presented"],
    "level_2": ["Scientific findings / information is presented; efficacy, superiority, risk reduction, faster onset"],
    "level_3": ["Scientific data, research, studies or information are INTRODUCED TO ESTABLISH EXPERTISE BEFORE the findings of those studies are presented. -At least one fact is used to provide credibility during the introduction. Language used suggests the company conducted the research."],
    "level_4": ["Independent, Scientific data, research, studies or information are INTRODUCED TO ESTABLISH EXPERTISE BEFORE the findings of those studies are presented. -Multiple facts are used to provide credibility during the introduction. -Language used suggests the research is independent; It, they, the."]
  }

CLOSING_OUTCOME_STATEMENT_DEFINITION = (
    "The CLOSING & OUTCOME section encompasses the final part of the conversation,"
    " where the REP seeks to conclude the interaction with a commitment, next steps, "
    "or an agreement from the HCP. This can involve multiple closing questions or"
    " statements aimed at gaining a form of agreement or plan from the HCP."
    " The outcome reflects the HCP's response to these closing efforts, "
    "indicating their level of interest, agreement, or the agreed-upon actions "
    "following the conversation. The concluding phase of the conversation where "
    "the REP asks closing questions to secure a commitment or agree on next steps."
    " The outcome captures the HCP's responses, indicating their agreement, "
    "interest, or the actions they plan to take following the interaction.")

CLOSING_STATEMENT_LEVEL = {
    "level_1": [
      "No commitment asked for or requested",
      "Sending information",
      "None action based requests are this level"
    ],
    "level_2": [
      "Commitment to another meeting is requested",
      "Tries to arrange the next meeting"
    ],
    "level_3": ["Commitment to do something specific asked for, e.g. Will you now use my product?"],
    "level_4": ["Encourages HCP to volunteer a commitment, e.g. what do you think should happen next?"]
  }
OUTCOME_STATEMENT_LEVEL = {
    "level_1": [
      "Outcomes are nebulous, non-descript and nothing tangible",
      "Outcome is a “No” response to another meeting",
      "Outcome is a “No” to a specific action based request"
    ],
    "level_2": ["A “Yes” is given to a request for another meeting."],
    "level_3": ["A “Yes” is given to a specific action based request to do something other than attend a meeting."],
    "level_4": ["The HCP volunteers to do something different as a result of the conversation; makes notes, describes a specific patient profile, calls a colleague, speaks to a colleague"]
  }

ADDITIONAL_INFORMATION_FOR_CLASSIFICATION = (
    "Each dialogues should be evaluated within its category for strategic "
    "implication, effectiveness, and alignment with interaction objectives.\n"
    "REP's statements are the primary focus for OPENING, QUESTIONING, and PRESENTING categories."
    " HCP responses should be considered in the CLOSING_OUTCOME category to assess the interaction's conclusiveness and commitment level.\n "
    "Note the placement of statements: "
    "OPENING statements occur at the beginning, and CLOSING_OUTCOME at the end, "
    "with QUESTIONING and PRESENTING potentially throughout the dialogue. "
    "Some dialogues may fit into multiple categories; "
    "apply the criteria thoughtfully, considering the segmented nature of transcripts and "
    "the intended impact of each statement."
)

ADDITIONAL_INFORMATION_FOR_CLASSIFICATION_WITHOUT_OPENING_CLOSING = (
    "Each dialogues should be evaluated within its category for strategic "
    "implication, effectiveness, and alignment with interaction objectives.\n"
    "Focus strictly on REP's statements for the 'QUESTIONING' and 'PRESENTING' categories. Ignore HCP responses.\n"
)

ADDITIONAL_INFORMATION_FOR_CLASSIFICATION_WITHOUT_OPENING = (
    "Each dialogues should be evaluated within its category for strategic "
    "implication, effectiveness, and alignment with interaction objectives.\n"
    "Focus strictly on REP's statements for the 'QUESTIONING', and 'PRESENTING' categories. Ignore HCP responses.\n"
    "Evaluate REP statements for the 'CLOSING & OUTCOME' category based on content that aims for a productive conversation conclusion. "
    "Due to the nature of the transcripts being segmented into multiple parts with potential overlaps.\n"
    "The 'CLOSING & OUTCOME' statements may primarily appear towards the end of the final segments.\n"
)

ADDITIONAL_INFORMATION_FOR_CLASSIFICATION_WITHOUT_CLOSING = (
    "Each dialogues should be evaluated within its category for strategic "
    "implication, effectiveness, and alignment with interaction objectives.\n"
     "Focus strictly on REP's statements for the 'OPENING', 'QUESTIONING', and 'PRESENTING' categories. Ignore HCP responses.\n"
     "The 'OPENING' statements primarily appear towards the start of the initial segments.\n"
)


def get_important_note(not_included_statements=""):
    if 'OPENING' in not_included_statements:
        return ADDITIONAL_INFORMATION_FOR_CLASSIFICATION_WITHOUT_OPENING
    elif 'CLOSING' in not_included_statements:
        return ADDITIONAL_INFORMATION_FOR_CLASSIFICATION_WITHOUT_CLOSING
    elif 'EXTREME_END' in not_included_statements:
        return ADDITIONAL_INFORMATION_FOR_CLASSIFICATION_WITHOUT_OPENING_CLOSING
    return ADDITIONAL_INFORMATION_FOR_CLASSIFICATION
