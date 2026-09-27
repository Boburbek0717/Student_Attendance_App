"""Central SAT seed, based on College Board content-domains (2026-09-27).

https://satsuite.collegeboard.org/practice/content-domains
Codes are local stable identifiers, not official College Board identifiers.
"""
SAT = {
    "reading-writing": ("Reading and Writing", {
        "information-ideas": ("Information and Ideas", ["Central Ideas and Details", "Inferences", "Command of Evidence"]),
        "craft-structure": ("Craft and Structure", ["Words in Context", "Text Structure and Purpose", "Cross-Text Connections"]),
        "expression-ideas": ("Expression of Ideas", ["Rhetorical Synthesis", "Transitions"]),
        "standard-conventions": ("Standard English Conventions", ["Boundaries", "Form, Structure, and Sense"]),
    }),
    "math": ("Math", {
        "algebra": ("Algebra", ["Linear equations in one variable", "Linear functions", "Linear equations in two variables", "Systems of two linear equations in two variables", "Linear inequalities in one or two variables"]),
        "advanced-math": ("Advanced Math", ["Nonlinear functions", "Nonlinear equations in one variable", "Systems of equations in two variables", "Equivalent expressions"]),
        "problem-solving-data": ("Problem-Solving and Data Analysis", ["Ratios, rates, proportional relationships, and units", "Percentages", "One-variable data: Distributions and measures of center and spread", "Two-variable data: Models and scatterplots", "Probability and conditional probability", "Inference from sample statistics and margin of error", "Evaluating statistical claims: Observational studies and experiments"]),
        "geometry-trigonometry": ("Geometry and Trigonometry", ["Area and volume", "Lines, angles, and triangles", "Right triangles and trigonometry", "Circles"]),
    }),
}


def seed(connection):
    from app.question_bank.models import Bank, Section, Domain, Skill
    bank = connection.execute(Bank.__table__.insert().values(code="sat", name="SAT")).inserted_primary_key[0]
    for code, (name, domains) in SAT.items():
        section = connection.execute(Section.__table__.insert().values(bank_id=bank, code=code, name=name)).inserted_primary_key[0]
        for domain_code, (domain_name, skills) in domains.items():
            domain = connection.execute(Domain.__table__.insert().values(section_id=section, code=domain_code, name=domain_name)).inserted_primary_key[0]
            for position, skill_name in enumerate(skills, 1):
                connection.execute(Skill.__table__.insert().values(domain_id=domain, code=f"skill-{position}", name=skill_name))
