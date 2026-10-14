"""(22MN6HS302) Gender Sensitization — VNR VJIET B.Tech. AIML R22, V Semester.

Units are the syllabus's five modules; topics are the module bullets.
"""

from __future__ import annotations

from skillforge.teacher.content._build import concept, lesson, question, subject, topic, unit

GENDER_INTRO = topic(
    "gs-definition",
    "Definition of Gender and Basic Gender Concepts and Terminology",
    "Distinguishing sex from gender, the core vocabulary of gender studies, and what it means for gender to "
    "be socially constructed.",
    level="Beginner",
    lesson=lesson(
        "Gender studies begins with a distinction: sex refers to biological characteristics, while gender "
        "refers to the roles, behaviours, expectations and identities that a society attaches to being a "
        "woman, a man or another gender.",
        [
            "Because gender is socially constructed, ideas about masculinity and femininity are learned "
            "through family, school, media and culture, and they differ across societies and change over "
            "time. A gender stereotype is a generalized belief about what people of a particular gender are "
            "like or should do.",
            "Gender equality means equal rights, responsibilities and opportunities. Gender equity is about "
            "fairness: recognizing that people start from different positions and may need different support "
            "to reach equal outcomes.",
        ],
        [
            "Sex is biological; gender is social.",
            "Gender norms are learned and vary across cultures and time.",
            "Equity (fair support) is the route to equality (equal outcomes).",
        ],
    ),
    concepts={
        "sex-gender": concept(
            "Sex and gender",
            "Ask whether a difference comes from biology (sex) or from social expectations about roles and "
            "behaviour (gender). Most everyday 'rules' about who does what are gender, not sex.",
        ),
        "terminology": concept(
            "Gender concepts and terminology",
            "A stereotype generalizes about a gender; equality means equal rights and opportunities; equity "
            "means fair, sometimes different, support to reach equal outcomes.",
        ),
        "construction": concept(
            "Social construction of gender",
            "Gender roles are taught and reinforced (by families, institutions, media), so they can also be "
            "questioned and changed.",
        ),
    },
    questions=[
        question(
            "gs-1", 1, "sex-gender",
            "Which statement best distinguishes sex from gender?",
            ["They mean exactly the same thing",
             "Gender is biological, while sex is social",
             "Sex refers to biological characteristics; gender refers to socially constructed roles, "
             "behaviours and expectations",
             "Sex refers only to a person's legal identity"], 2,
            "Sex is about biology; gender is about the meanings, roles and expectations a society builds "
            "around it.",
        ),
        question(
            "gs-2", 1, "terminology",
            "What is a gender stereotype?",
            ["A generalized belief about the characteristics or roles that people of a particular gender have "
             "or should have",
             "A law guaranteeing equal pay",
             "A biological difference between the sexes",
             "A person's chosen name"], 0,
            "Stereotypes such as 'boys are better at maths' or 'girls are more caring' assign traits to a "
            "whole group and limit individuals.",
        ),
        question(
            "gs-3", 2, "construction",
            "What does it mean to say that gender is socially constructed?",
            ["Gender roles are fixed by biology and cannot change",
             "Ideas about masculinity and femininity are learned through family, school, media and culture, "
             "and vary across societies and over time",
             "Only governments decide what gender roles are",
             "Gender has no influence on people's opportunities"], 1,
            "Because gender norms are learned, they differ between cultures and generations, and they can be "
            "examined and changed.",
        ),
        question(
            "gs-4", 2, "terminology",
            "How does gender equity differ from gender equality?",
            ["Equity means treating everyone identically in every case",
             "Equity applies only to women",
             "Equity is about biological sex rather than gender",
             "Equity focuses on fairness: providing the support people need to reach equal outcomes, which "
             "may mean different support"], 3,
            "Equality is the goal of equal rights and opportunities; equity recognizes unequal starting points "
            "and adjusts support to reach that goal.",
        ),
        question(
            "gs-5", 3, "construction",
            "A school routinely asks girls to decorate classrooms and boys to move furniture. From a gender "
            "sensitization perspective, what is the main concern?",
            ["There is no concern; the tasks simply match ability",
             "It reinforces stereotyped roles and limits the skills each group is encouraged to develop",
             "It breaks rules about sustainable development",
             "It only matters if it happens outside school"], 1,
            "Routinely assigning tasks by gender teaches students that some work 'belongs' to one gender, "
            "narrowing the skills and aspirations each group develops.",
        ),
        question(
            "gs-6", 3, "sex-gender",
            "Which of these is an example of gender rather than sex?",
            ["Differences in chromosomes",
             "The ability to become pregnant",
             "The expectation that household work is mainly a woman's responsibility",
             "Differences in reproductive organs"], 2,
            "Who does household work is a social expectation, not a biological fact, so it is a matter of "
            "gender. The other options are biological, so they concern sex.",
        ),
    ],
)

SUBJECT = subject(
    "gender-sensitization",
    "22MN6HS302",
    "Gender Sensitization",
    "GS",
    "mandatory",
    "Key issues and debates in gender studies: gender concepts, roles and relations, development issues, "
    "gender-based violence, and gender and culture.",
    [
        unit(1, "Introduction to Gender", [
            GENDER_INTRO,
            topic("gs-attitudes", "Exploring Attitudes towards Gender",
                  "Examining our own assumptions about gender.", level="Beginner"),
            topic("gs-social-construction", "Social Construction of Gender",
                  "How gender is learned and reinforced.", level="Beginner"),
        ]),
        unit(2, "Gender Roles and Relations", [
            topic("gs-roles", "Types of Gender Roles", "Productive, reproductive and community roles."),
            topic("gs-roles-matrix", "Gender Roles and Relationships Matrix",
                  "Mapping roles and relationships."),
            topic("gs-labour", "Gender-based Division and Valuation of Labour",
                  "Who does which work, and how it is valued."),
        ]),
        unit(3, "Gender Development Issues", [
            topic("gs-issues", "Identifying Gender Issues", "Recognizing gender issues in context."),
            topic("gs-language", "Gender Sensitive Language", "Language that includes rather than excludes."),
            topic("gs-governance", "Gender, Governance and Sustainable Development",
                  "Gender in governance and development."),
            topic("gs-human-rights", "Gender and Human Rights", "Gender equality as a human right."),
            topic("gs-mainstreaming", "Gender and Mainstreaming", "Building gender into policy and practice."),
        ]),
        unit(4, "Gender-based Violence", [
            topic("gs-violence-concept", "The Concept of Violence", "What counts as violence."),
            topic("gs-violence-types", "Types of Gender-based Violence", "Forms of gender-based violence."),
            topic("gs-violence-development", "Gender, Development and Violence",
                  "The relationship between gender, development and violence."),
            topic("gs-violence-rights", "Gender-based Violence from a Human Rights Perspective",
                  "Violence as a human rights issue."),
        ]),
        unit(5, "Gender and Culture", [
            topic("gs-film-media", "Gender and Film; Gender and Electronic Media",
                  "Representation of gender on screen."),
            topic("gs-advertising-literature", "Gender and Advertisement; Gender and Popular Literature",
                  "Representation of gender in advertising and literature."),
            topic("gs-knowledge", "Gender and the Structure of Knowledge: Questions for Historians and "
                  "Others, Reclaiming a Past, Writing Other Histories", "Whose knowledge, whose history."),
        ]),
    ],
    unit_label="Module",
)
