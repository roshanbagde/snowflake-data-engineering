"""
Bulk-insert 100 additional questions into thinkpark.db.
Run: python add_questions.py
Safe to re-run — skips any question whose text already exists.
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "thinkpark.db"

# Each entry: topic, age_group, level, type, question_text, context, hint, sample_answer,
#             discussion_points (list), follow_up_questions (list), tags
QUESTIONS = [

    # ══════════════════════════════════════════════════════════════════════════
    # SEEDLINGS  (5-7)  — 20 questions
    # ══════════════════════════════════════════════════════════════════════════

    ("🧠 Critical Thinking", "Seedlings", "simple", "what_if",
     "What if animals could talk? What do you think your favourite animal would say to you?",
     "", "Think about what that animal does all day. What might it want to tell you?",
     "Any creative answer works! The key is to think about the animal's point of view — not just what you want to hear.",
     ["What would animals tell us about how we treat them?", "Would the world be better or worse if animals could talk?", "Which animal would you most want to have a conversation with?"],
     ["What would YOU say to the animal?", "Would animals and humans become friends or have arguments?"],
     "imagination,empathy,animals,perspective"),

    ("❤️ Emotional Intelligence", "Seedlings", "simple", "scenario",
     "Your little brother or sister breaks your favourite toy by accident. How do you feel, and what do you do?",
     "It was not done on purpose.",
     "Can you feel two things at once — like sad AND understanding? Both are okay.",
     "It is normal to feel upset. But since it was an accident, the kind thing is to take a breath, say how you feel calmly, and not shout. You can be sad about the toy AND still be kind.",
     ["Is it okay to feel angry even when something is an accident?", "What is the difference between an accident and doing something on purpose?", "How do YOU feel when you accidentally hurt someone?"],
     ["What if your brother or sister cried because they felt bad — what would you do?", "How would you like someone to react if YOU broke something by accident?"],
     "emotions,empathy,siblings,accidents"),

    ("💬 Communication", "Seedlings", "simple", "reflection",
     "Think of a time you needed help but did not ask for it. What stopped you?",
     "", "Was it feeling shy? Thinking no one would help? Not knowing how to ask?",
     "Many people find it hard to ask for help. Common reasons: feeling embarrassed, not wanting to seem weak, or not knowing how to ask. Asking for help is actually brave and smart.",
     ["Why do some people think asking for help is a sign of weakness?", "Who are the people you find easiest to ask for help? Why?", "How does it feel when someone asks YOU for help?"],
     ["How could you make it easier for others to ask you for help?", "What is one thing you could ask for help with today?"],
     "communication,asking for help,courage,reflection"),

    ("🤝 Social Skills & Teamwork", "Seedlings", "simple", "scenario",
     "A new child joins your class and sits alone at lunch because they do not know anyone yet. What do you do?",
     "You remember your first day at a new place.",
     "Think about how that child feels. Would you want someone to come to you?",
     "Sitting with them and saying hello is one of the kindest things you can do. You do not need to be best friends — just being friendly helps enormously on a hard first day.",
     ["How do you think the new child feels?", "What is the difference between being polite and being a true friend?", "Why do some people not approach new children even when they want to?"],
     ["What if the new child was very quiet and did not talk much?", "How would YOU feel if no one sat with you on your first day?"],
     "kindness,inclusion,friendship,empathy"),

    ("🏆 Leadership & Decisions", "Seedlings", "simple", "scenario",
     "Your friends cannot agree on which game to play. Everyone wants something different. What do you do?",
     "", "Think about a way that is fair to everyone, not just yourself.",
     "You could suggest taking turns, doing a quick vote, or trying one game for 10 minutes then switching. Good leaders find solutions that include everyone.",
     ["What makes a decision feel fair to everyone?", "Is it always possible for everyone to get what they want?", "How does it feel when your idea is chosen versus when it is not?"],
     ["What if your idea loses the vote — do you still play happily?", "What if one friend keeps complaining even after a fair vote?"],
     "fairness,compromise,leadership,group decisions"),

    ("🎨 Creativity & Problem Solving", "Seedlings", "simple", "creative",
     "Design your dream bedroom. What would be in it, and what one thing would make it magical?",
     "", "Do not just think about toys — think about how you want to FEEL in that room.",
     "Any creative answer is right. The interesting part is the WHY — what does your choice say about what you love and value?",
     ["What does your design say about what matters to you?", "What is the difference between what you NEED in a room and what you WANT?", "If a friend designed their room very differently, would either of you be wrong?"],
     ["What would the room look like if you designed it for someone else?", "What one thing in your current bedroom do you love most?"],
     "creativity,imagination,design,self-expression"),

    ("⚖️ Ethics & Values", "Seedlings", "simple", "dilemma",
     "Your friend gives you a biscuit but says not to share it with anyone. Another friend nearby is hungry and has nothing to eat. What do you do?",
     "", "Think about what is fair to both friends. Is there a way to keep both happy?",
     "This is a genuine dilemma — both choices have consequences. You could ask the first friend if it is okay to share. Or explain the situation. Doing nothing while someone is hungry is also a choice.",
     ["Why did your friend say not to share?", "What is the difference between a promise and a rule?", "Is it ever okay to break a small promise to do something kind?"],
     ["What would you want someone to do if YOU were the hungry friend?", "What if you asked the first friend and they still said no?"],
     "fairness,promises,kindness,dilemma"),

    ("🪞 Self-Awareness", "Seedlings", "simple", "reflection",
     "What is one thing you are really good at? How did you get good at it — did it come naturally or did you have to practise?",
     "", "Think honestly. Did it feel easy at first, or did you have to keep trying?",
     "Most skills take practice even when they feel natural now. Noticing HOW you got good at something helps you get good at other things too.",
     ["Does everyone have something they are good at?", "What is the difference between talent and hard work?", "Can you get better at something you are currently bad at?"],
     ["What is one thing you WANT to get better at?", "Who helped you become good at that thing?"],
     "self-awareness,growth mindset,skills,reflection"),

    ("💰 Financial Literacy", "Seedlings", "simple", "scenario",
     "You have ₹20. A chocolate costs ₹15 and a pencil costs ₹10. You can only buy one. Which do you choose and why?",
     "", "Think about need vs want. Which one is more useful tomorrow?",
     "Both are fine choices — but thinking about WHY you choose is important. Do you really need chocolate? Do you have pencils at home? Good decisions think ahead.",
     ["What is the difference between something you need and something you want?", "How do you feel after eating chocolate vs after using a pencil for a week?", "What would happen if you always chose the fun thing over the useful thing?"],
     ["What if the pencil was for school work due tomorrow?", "Would your answer change if you already had 10 pencils at home?"],
     "money,needs vs wants,decisions,financial literacy"),

    ("🌍 Environment & Society", "Seedlings", "simple", "what_if",
     "What if trees could walk away whenever someone tried to cut them down? What would the world look like?",
     "", "Think about where trees would go. Would humans change how they behave?",
     "This fun question hides a real one: why do we cut trees down? And what happens to the world without them? Walking trees would force humans to take nature more seriously.",
     ["Why are trees important to us?", "Why do people cut trees down?", "What could we do to protect trees without them needing to run away?"],
     ["Where would the trees go?", "Would people start being kinder to trees if trees could respond?"],
     "environment,nature,imagination,consequences"),

    ("🧠 Critical Thinking", "Seedlings", "simple", "scenario",
     "Your friend says the moon is made of cheese. How do you find out if that is really true?",
     "", "Think about what sources you trust. Who would actually know the answer?",
     "You would look it up in a book, ask a trusted adult, or find a reliable website. We should not believe everything we hear — even from friends — without checking.",
     ["How do you know when something is true?", "Is it okay to disagree with a friend if you think they are wrong?", "What is the difference between a fact and an opinion?"],
     ["What if the book and your friend say different things?", "How do you think the moon was actually formed?"],
     "critical thinking,truth,checking facts,curiosity"),

    ("❤️ Emotional Intelligence", "Seedlings", "simple", "dilemma",
     "You feel like crying at school but do not want anyone to see you cry. Is it okay to cry? What do you do?",
     "", "Think about WHY you do not want to be seen. Is crying something to be ashamed of?",
     "Crying is a normal, healthy emotion. It is okay to cry. If you want privacy, you can ask to go to the bathroom or find a quiet spot. Hiding feelings completely can make them worse.",
     ["Why do some people feel embarrassed about crying?", "Does crying mean you are weak?", "What are other ways to let out big feelings?"],
     ["Who at school would be safe to talk to if you were upset?", "How do you feel after a good cry?"],
     "emotions,vulnerability,crying,self-regulation"),

    ("💬 Communication", "Seedlings", "simple", "creative",
     "If you could send one message to every child in the world, what would you say?",
     "", "Think carefully — this message goes to children who are very different from you. What matters to everyone?",
     "This is open-ended. The most powerful messages are usually simple, honest, and universal. The key is thinking about what ALL children share.",
     ["What do all children in the world have in common?", "What would a child in a very poor country need to hear?", "What would a child in a conflict zone need to hear?"],
     ["Would you send one message or different messages to different children?", "If a child from another country sent YOU a message, what do you hope they would say?"],
     "communication,empathy,global thinking,creativity"),

    ("🤝 Social Skills & Teamwork", "Seedlings", "simple", "dilemma",
     "You are playing a game and you accidentally hurt another player. Nobody saw it happen. Do you say sorry?",
     "", "Does it matter if nobody saw it? Does the other person know they were hurt?",
     "If someone is hurt, they deserve to know you care — whether or not anyone is watching. Saying sorry when no one is watching is one of the truest tests of honesty.",
     ["Why do some people only apologise when they are caught?", "How does the hurt person feel if they never find out what happened?", "What does it mean to have integrity?"],
     ["What if the other player did not seem to notice?", "Have you ever felt better after apologising for something even when you did not have to?"],
     "honesty,apology,integrity,games"),

    ("🏆 Leadership & Decisions", "Seedlings", "simple", "what_if",
     "If you were the principal of your school for one day, what one rule would you change and why?",
     "", "Think about rules that feel unfair or unhelpful. Why does that rule exist in the first place?",
     "A good answer includes the reason WHY the rule should change and what would be better. Good leaders think about consequences before making changes.",
     ["Why do schools have rules?", "Who does the rule help or protect?", "What could go wrong if you removed a rule?"],
     ["What is one rule you actually think is good and should stay?", "What rule would YOU make that does not exist yet?"],
     "leadership,rules,fairness,decision making"),

    ("🎨 Creativity & Problem Solving", "Seedlings", "simple", "what_if",
     "What if you woke up one morning and you could speak any language in the world? Which would you choose first, and what is the first thing you would say?",
     "", "Think about WHO you would want to talk to and WHY.",
     "Any answer is right. The interesting part is thinking about what language opens up — people, books, places, ideas you could not reach before.",
     ["What language do the most people in the world speak?", "What could you do with a new language that you cannot do now?", "Why might someone want to learn a language besides their own?"],
     ["What if everyone in the world already knew all languages?", "What is one language you have always been curious about?"],
     "creativity,language,communication,imagination"),

    ("⚖️ Ethics & Values", "Seedlings", "simple", "scenario",
     "Your friend tells you a secret. Later, you find out keeping that secret could hurt someone else. What do you do?",
     "", "Think about who could get hurt and how badly. Not all secrets are equal.",
     "Small secrets are usually fine to keep. But if someone could get seriously hurt, telling a trusted adult is the right thing — even if it feels like breaking a promise. Safety comes first.",
     ["Is every secret equally important to keep?", "Who should you tell when a secret involves danger?", "How would your friend feel if you told? How would you feel if you did not tell and someone got hurt?"],
     ["What is the difference between a secret and a surprise?", "What would you say to your friend afterwards?"],
     "ethics,secrets,trust,safety"),

    ("🪞 Self-Awareness", "Seedlings", "simple", "reflection",
     "What is one thing that makes you feel scared? What is one thing that helps you feel brave?",
     "", "Be honest — everyone is scared of something. Knowing what helps you is just as important.",
     "Bravery is not the absence of fear — it is doing something even when you ARE scared. Knowing your own fear and your own source of courage is a sign of self-awareness.",
     ["Is everyone scared of something?", "Does being brave mean you are not scared?", "What would you do if your 'brave thing' was not available?"],
     ["What is something you were scared of before but are not scared of now?", "How could you help a friend who is scared of the same thing?"],
     "self-awareness,courage,fear,emotions"),

    ("💰 Financial Literacy", "Seedlings", "simple", "creative",
     "Someone gives you ₹100 and says you must spend it — but it has to help at least one other person. What do you do?",
     "", "Think about what someone else actually needs, not just what you would enjoy giving.",
     "Any generous answer works. The key insight is that helping someone effectively means thinking about what THEY need, not what you would want. That is the beginning of good decision-making with money.",
     ["How do you find out what someone actually needs?", "Is giving money always the best way to help?", "What is the difference between helping and showing off?"],
     ["What if the person you wanted to help said they did not want it?", "Can you help someone without spending money?"],
     "generosity,financial literacy,kindness,decisions"),

    ("🌍 Environment & Society", "Seedlings", "simple", "scenario",
     "You see a stranger dropping a plastic bottle on the ground right in front of you. What do you do?",
     "", "Think about what you could say that is kind but also makes the point.",
     "Picking it up yourself sets a good example. Politely saying 'Excuse me, I think you dropped this' is brave but kind. Staying silent is also a choice — and that is worth thinking about.",
     ["Why do people litter?", "Is it your responsibility to say something to a stranger?", "How does one piece of litter affect a whole area?"],
     ["What if the stranger got annoyed at you for saying something?", "What if there were no bins nearby — what should the person have done?"],
     "environment,civic responsibility,courage,litter"),

    # ══════════════════════════════════════════════════════════════════════════
    # EXPLORERS  (8-10)  — 20 questions
    # ══════════════════════════════════════════════════════════════════════════

    ("🧠 Critical Thinking", "Explorers", "medium", "debate_starter",
     "Should every child get the same amount of pocket money, or should it depend on age and responsibilities?",
     "", "Think about what is FAIR. Is fair always the same as equal?",
     "Equal means everyone gets the same. Fair means everyone gets what they need or have earned. These are different concepts — and both have merit in different situations.",
     ["What is the difference between equality and fairness?", "Should older children automatically get more?", "Who should decide how much pocket money a child gets?"],
     ["What should pocket money be used for — only fun, or also responsibilities?", "Do you think YOUR pocket money is fair?"],
     "fairness,equality,money,debate"),

    ("❤️ Emotional Intelligence", "Explorers", "medium", "scenario",
     "Your best friend gets the lead role in the school play and you do not. You feel happy for them but also disappointed for yourself. Is it okay to feel both at once?",
     "", "Think about whether feelings can contradict each other. Do they have to?",
     "Yes — feeling two conflicting emotions at once is completely normal and is called being human. Acknowledging BOTH feelings honestly (rather than pretending to feel only one) is emotional maturity.",
     ["Can you genuinely feel happy for someone while also feeling sad for yourself?", "What would happen if you pretended to feel only happy?", "What does your friend need from you right now?"],
     ["How would you want your friend to react if the situation were reversed?", "What would you do with your disappointment so it does not affect your friendship?"],
     "emotional intelligence,mixed feelings,friendship,envy"),

    ("💬 Communication", "Explorers", "medium", "scenario",
     "You know the answer in class but feel too nervous to raise your hand. What stops you — and how could you get past it?",
     "", "Think about what you are afraid of. Is the fear realistic?",
     "Common fears: being wrong and embarrassed, being judged, or seeming like a 'show-off'. Understanding WHY you hold back is the first step to working through it. Starting with smaller moments builds confidence.",
     ["What is the worst that could actually happen if you answer and get it wrong?", "Why do some people find speaking up easy and others find it hard?", "What would you think of a classmate who got an answer wrong?"],
     ["What is one small way you could practise speaking up more?", "Does everyone who raises their hand feel confident — or do some of them feel nervous too?"],
     "confidence,communication,fear of speaking,courage"),

    ("🤝 Social Skills & Teamwork", "Explorers", "medium", "dilemma",
     "Your group of friends starts making fun of another child's lunch. You do not find it funny. What do you do?",
     "", "Think about what happens if you stay silent. Is silence the same as agreeing?",
     "Staying silent when others are unkind often reads as agreement — and makes the target feel more alone. You do not have to make a big speech: 'Come on, let's talk about something else' is often enough.",
     ["What is the difference between staying silent and agreeing?", "Why do people laugh along at things they do not find funny?", "What do you think the child with the lunch is feeling?"],
     ["What if one of your close friends was the main one making fun?", "What could you say that redirects without making a big scene?"],
     "peer pressure,courage,kindness,bystander"),

    ("🏆 Leadership & Decisions", "Explorers", "medium", "scenario",
     "You are leading a group project and one team member keeps shooting down everyone else's ideas. What do you do?",
     "The project matters and the team is getting frustrated.", "Think about how to address the behaviour without attacking the person.",
     "Acknowledge the team member's concerns (they may have valid points), but set a group norm: ideas get heard fully before feedback is given. A good leader creates safety for everyone to contribute.",
     ["Why might someone keep dismissing others' ideas?", "What is the difference between constructive criticism and being negative?", "How do you keep the team's energy up?"],
     ["What if that person also had the best technical skills on the team?", "How would you give feedback to that person privately?"],
     "leadership,team dynamics,conflict,communication"),

    ("🎨 Creativity & Problem Solving", "Explorers", "medium", "creative",
     "Design a new school subject that does not exist yet but should. What would students learn in it, and why is it important?",
     "", "Think about what skills you wish you were taught that no one teaches in school.",
     "This is open-ended. Strong answers explain WHY the subject matters, not just what is in it. Examples: emotional skills, money management, cooking, logical thinking, how the internet works.",
     ["What skills do adults need that school never teaches?", "Who would decide what goes into this new subject?", "Would you make it optional or compulsory?"],
     ["Who would teach this subject? What qualifications would they need?", "How would you test if a student is 'good' at it?"],
     "creativity,education,design,problem solving"),

    ("⚖️ Ethics & Values", "Explorers", "medium", "dilemma",
     "You see a classmate copying answers from another student during a test. The teacher does not notice. Do you say something?",
     "", "Think about who is affected if you say something — and who is affected if you do not.",
     "Saying nothing lets unfairness continue. Telling the teacher directly may feel like 'telling on' someone. Options include telling the teacher privately, or speaking to the classmate afterwards. There is no easy answer.",
     ["Is it fair to the students who studied honestly?", "What is the difference between telling to get someone in trouble and telling because it is unfair?", "How would you feel if someone copied YOUR answers?"],
     ["What if the classmate was your friend?", "What if you had once done something similar — would that change your decision?"],
     "ethics,cheating,fairness,integrity"),

    ("🪞 Self-Awareness", "Explorers", "medium", "reflection",
     "Think of a time you lost your temper. What happened? What triggered it — and what would you do differently now?",
     "", "Try to remember the exact moment you felt yourself start to lose control.",
     "Understanding your own anger patterns — what triggers them and what they feel like — is the first step to managing them. Most people find they have predictable triggers.",
     ["What does it feel like in your body just before you lose your temper?", "Does losing your temper usually help or make things worse?", "What is one strategy that works for you when you feel anger building?"],
     ["How do the people around you react when you lose your temper?", "Have you ever regretted something you said in anger?"],
     "self-awareness,anger management,reflection,emotional regulation"),

    ("💰 Financial Literacy", "Explorers", "medium", "scenario",
     "Your school is having a fundraiser for a good cause. You want to help but you have no money. How can you still make a difference?",
     "", "Think beyond money. What else do you have to contribute?",
     "You can contribute time, energy, skills, and creativity — organise, promote, volunteer, make things to sell, collect donations from neighbours. Money is not the only resource.",
     ["What resources do you have besides money?", "Which is more valuable — money or time?", "What is the purpose of a fundraiser beyond just collecting money?"],
     ["What if the fundraiser still fell short even after everyone tried their best?", "How would you feel if you contributed something non-monetary and the fundraiser succeeded?"],
     "financial literacy,resourcefulness,volunteering,community"),

    ("🌍 Environment & Society", "Explorers", "medium", "what_if",
     "What if your school had no electricity for one whole week? How would you learn, and what would be easier or harder?",
     "", "Think about everything that depends on electricity in your school day.",
     "No projectors, computers, or fans. But also: more creativity, outdoor learning, human conversation, handwriting. What we find hard without technology reveals how much we rely on it — and what existed before.",
     ["What would be impossible without electricity in school?", "How did students learn 100 years ago?", "What skills do we lose because we rely so much on technology?"],
     ["Would you prefer this to a normal school week?", "What would you do in your free time at home during that week?"],
     "environment,technology,resilience,critical thinking"),

    ("🧠 Critical Thinking", "Explorers", "medium", "scenario",
     "A friend tells you an amazing 'true story' they heard from someone else. Later, a book says the opposite is true. Who do you believe, and how do you find the truth?",
     "", "Think about which source is more likely to be accurate — and why.",
     "The book is likely more reliable, but you should still check: when was it written, who wrote it, and what is their expertise? Stories passed between people often get changed. Primary sources are most reliable.",
     ["Why do stories change as they get passed from person to person?", "What makes a book more trustworthy than a rumour?", "Is it okay to tell your friend they might be wrong?"],
     ["What if your friend insists they are right even after you find the evidence?", "Can books ever be wrong?"],
     "critical thinking,sources,fact-checking,information"),

    ("❤️ Emotional Intelligence", "Explorers", "medium", "reflection",
     "Who is someone in your life who is always kind to you? What exactly do they DO that makes you feel cared for? Could you do that for someone else?",
     "", "Think about specific actions — not just 'they are nice'. What do they actually do?",
     "Kindness is in the details: remembering what matters to someone, listening without rushing, noticing when you are quiet. Identifying specific acts makes kindness something you can practise on purpose.",
     ["Why do some people make us feel more cared for than others?", "Is kindness something you are born with or something you practise?", "Who in your life might need more kindness right now?"],
     ["What is one specific thing you could do for someone this week?", "Why do we sometimes take kind people for granted?"],
     "kindness,relationships,emotional intelligence,gratitude"),

    ("💬 Communication", "Explorers", "medium", "what_if",
     "What if you had to explain what the colour blue looks like to someone who has never seen colour? How would you do it?",
     "", "Think about all your senses — not just vision. What does blue FEEL like, sound like, remind you of?",
     "This is an exercise in description and empathy. You have to step outside your own experience. Blue might feel calm like cool water, sound like a gentle hum, smell like rain. Good communication bridges very different experiences.",
     ["What makes communication hard when two people have very different experiences?", "How do blind people experience the world without colour?", "Why is 'seeing it from someone else's perspective' so hard?"],
     ["How would you explain a sound to someone who has never heard anything?", "What does this tell us about how limited our own understanding can be?"],
     "communication,empathy,perspective,description"),

    ("🤝 Social Skills & Teamwork", "Explorers", "medium", "debate_starter",
     "Should parents have a say in who their children are friends with?",
     "", "Think about when parental guidance is helpful and when it might cross a line.",
     "Parents can offer perspective on what is safe. But friendships are personal, and learning to navigate them yourself is important for development. The answer likely sits between 'never interfere' and 'full control'.",
     ["What is the difference between parental guidance and control?", "Have your parents ever been right about a friend?", "At what age should children choose their own friends completely freely?"],
     ["What if a parent disliked a friend for a reason that seemed unfair?", "What responsibility do YOU have in choosing your friends wisely?"],
     "friendships,parents,autonomy,debate"),

    ("🏆 Leadership & Decisions", "Explorers", "medium", "dilemma",
     "You are captain of a sports team. You notice a newer player making mistake after mistake. Do you tell them directly, or wait for the coach?",
     "", "Think about how feedback feels when it comes from a peer vs an authority figure.",
     "Both options have merit. Speaking directly, kindly and privately can be faster and more comfortable for the player. But if it is not your role or you are not sure how to do it well, letting the coach handle it avoids making things worse.",
     ["What is the difference between feedback and criticism?", "How would YOU want to receive feedback if you were making mistakes?", "What makes feedback helpful vs hurtful?"],
     ["What if you gave feedback and the player got upset?", "What if the coach never noticed and the mistakes continued?"],
     "leadership,feedback,teamwork,communication"),

    ("🎨 Creativity & Problem Solving", "Explorers", "medium", "what_if",
     "What if you could invent one machine to solve any problem in your school? What problem would you pick and how would the machine work?",
     "", "Think about problems that keep coming up — not just once. What would make the biggest difference?",
     "Strong answers identify a real problem clearly, then imagine a solution that is actually possible (or at least logical). The problem-identification step is as important as the invention.",
     ["Why is choosing the right problem to solve so important?", "What problems do you notice at school that adults might not see?", "How would you know if your machine was working?"],
     ["What if the machine had an unexpected side effect?", "What problem in the world would you solve if you could only pick one?"],
     "creativity,problem solving,invention,school"),

    ("⚖️ Ethics & Values", "Explorers", "medium", "scenario",
     "You accidentally break something at a friend's house while playing. Your friend does not notice it happened. What do you do?",
     "", "Think about how you would feel carrying that secret. And how your friend would feel if they found out later.",
     "Telling the truth — even when it is uncomfortable — builds trust. Saying 'I accidentally broke this, I am so sorry' usually goes better than your friend discovering it later and wondering why you said nothing.",
     ["How does keeping a secret like this feel over time?", "How would your friend feel if they found out you knew and said nothing?", "What does honesty cost you in this moment — and what does it give you long-term?"],
     ["What if the thing broken was very valuable?", "What would you say — exactly — when telling your friend?"],
     "honesty,accidents,trust,communication"),

    ("🪞 Self-Awareness", "Explorers", "medium", "reflection",
     "What is a subject or skill you think you are bad at? Is it really true — or have you just not practised enough yet?",
     "", "Think about when you decided you were 'bad' at it. Was it after one try, or many?",
     "Most skills improve with practice. Calling ourselves 'bad at something' often happens after one bad experience or comparison with someone more advanced. Growth mindset means seeing potential, not fixed limits.",
     ["What is the difference between 'I cannot do this' and 'I cannot do this yet'?", "Why do people give up on things quickly?", "What would happen if you spent 10 minutes a day on this thing for one month?"],
     ["Has anyone ever told you that you WERE good at something you thought you were bad at?", "What is one thing you used to be bad at and are now better at?"],
     "growth mindset,self-awareness,learning,resilience"),

    ("💰 Financial Literacy", "Explorers", "medium", "dilemma",
     "You want a new video game that costs ₹1,500. Your parents say no for now. List three honest ways you could work toward getting it yourself.",
     "", "Think about what resources you have — time, skills, effort. What can you trade for money?",
     "Examples: do extra chores for pay, sell unused things, save birthday money, trade gaming time with neighbours for helping tasks. The goal is resourcefulness and earning, not just waiting.",
     ["What is the difference between earning and just asking?", "Does getting something you saved up for feel different from getting it as a gift?", "Are there things you could sell or do without buying?"],
     ["How long would it take to save up at a realistic pace?", "What if your parents then said they would match whatever you saved?"],
     "financial literacy,saving,earning,resourcefulness"),

    ("🌍 Environment & Society", "Explorers", "medium", "scenario",
     "Your class organises a park clean-up. Only five out of thirty students show up. How do you feel — and what do you say to the others at school the next day?",
     "", "Think about what might have stopped the others — and how to encourage without making people feel guilty.",
     "Understanding why people do not show up (busy families, not caring, forgetting) matters. Shaming rarely works. Sharing what it was like and inviting them next time is more effective.",
     ["Why do people agree to things and then not follow through?", "Is five people doing a clean-up still worth it?", "How do you motivate people without guilting them?"],
     ["What would you do differently next time to get more people to come?", "Would you organise another one?"],
     "environment,civic engagement,motivation,community"),

    # ══════════════════════════════════════════════════════════════════════════
    # BUILDERS  (11-13)  — 20 questions
    # ══════════════════════════════════════════════════════════════════════════

    ("🧠 Critical Thinking", "Builders", "medium", "debate_starter",
     "Should social media platforms be banned for children under 13? Give strong arguments for both sides.",
     "", "Think about what social media gives and what it takes from younger children.",
     "For: exposure to harmful content, cyberbullying, addiction, distorted reality. Against: social connection, information access, creative expression, learning digital literacy. The real question is whether restrictions work — and whether age is the right filter.",
     ["How many children under 13 already use social media despite age limits?", "Who is responsible for protecting children online — parents, platforms, or government?", "What do children gain from social media that they lose without it?"],
     ["What would a healthy version of social media for under-13s look like?", "At what age should someone be allowed to make their own choices about what they consume online?"],
     "social media,debate,digital literacy,child safety"),

    ("❤️ Emotional Intelligence", "Builders", "medium", "scenario",
     "A close friend suddenly stops talking to you for no clear reason. They seem fine with everyone else. What do you do without making things worse?",
     "", "Think about the difference between reacting from hurt and responding thoughtfully.",
     "Going directly to them (privately, not by text) with a simple 'I feel like something has changed between us — did I do something?' is usually better than guessing, complaining to others, or dramatic confrontation.",
     ["Why do people 'ghost' people they care about instead of talking?", "What is the risk of confronting them directly?", "What is the risk of NOT confronting them?"],
     ["What if they deny anything is wrong?", "How long would you wait before deciding to move on from the friendship?"],
     "friendship,conflict,communication,emotional intelligence"),

    ("💬 Communication", "Builders", "hard", "scenario",
     "You think your teacher has explained something incorrectly in class. How do you bring it up without being disrespectful?",
     "", "Think about framing it as a question rather than a correction. Why does that matter?",
     "'Could you help me understand — I thought it was X, but I might be missing something?' opens dialogue. 'You are wrong' closes it. Being right matters less than being helpful and respectful in HOW you raise it.",
     ["Why might a teacher make an error?", "What is the difference between challenging an idea and attacking the person?", "Is it disrespectful to correct someone who has authority over you?"],
     ["What if the teacher still insists they are right after you raise it?", "How would you feel if a student corrected you respectfully when you were wrong?"],
     "communication,respect,authority,confidence"),

    ("🤝 Social Skills & Teamwork", "Builders", "medium", "dilemma",
     "Your two best friends have a serious argument with each other and both want you to take their side. What do you do?",
     "", "Think about what taking a side actually achieves — and who you are responsible to.",
     "Being in the middle of two friends' argument is genuinely hard. You are not obligated to judge. Being honest ('I love you both and I am not going to choose') is valid. Listening to each without encouraging blame is the most helpful role.",
     ["Is it fair for friends to put you in this position?", "What is the difference between being supportive and taking sides?", "What if one friend is clearly more in the wrong than the other?"],
     ["What would you say to each of them separately?", "What if they both get angry at you for not choosing?"],
     "friendship,conflict,loyalty,communication"),

    ("🏆 Leadership & Decisions", "Builders", "medium", "reflection",
     "Name one person you consider a strong leader — real or fictional. What specific qualities make them effective? Do you see any of those qualities in yourself?",
     "", "Try to name specific behaviours, not just 'they are brave' or 'they are smart'.",
     "Strong leadership traits: listening first, taking responsibility, communicating clearly, staying calm under pressure, inspiring others, and being honest about limits. Everyone has some — the question is which to develop.",
     ["Can someone be a leader without being in charge of anyone?", "Is confidence the same as leadership?", "What is the difference between a good leader and a popular one?"],
     ["What is one leadership quality you want to develop?", "Think of a time you led something — even small. What did you learn?"],
     "leadership,role models,self-awareness,qualities"),

    ("🎨 Creativity & Problem Solving", "Builders", "medium", "creative",
     "You have one week and ₹500 to visibly improve your neighbourhood in a lasting way. What do you do?",
     "", "Think about impact — what change would people notice and remember six months later?",
     "Good answers think about sustainability and community buy-in, not just the immediate gesture. Planting something, creating something people use, organising people — these last longer than cleaning alone.",
     ["What does 'lasting' mean in the context of community improvement?", "How do you get others to care about your project?", "What would you need beyond money to make this work?"],
     ["What if people in the neighbourhood were not interested?", "What improvement would have the biggest impact for the most people?"],
     "creativity,community,problem solving,civic responsibility"),

    ("⚖️ Ethics & Values", "Builders", "hard", "dilemma",
     "You find out a close friend has been cheating in exams for months. They beg you not to tell. What do you do, and why?",
     "", "Think about who is harmed by the cheating beyond just your friend's grades.",
     "The harm is real: unfair competition, false grades, your friend building on a weak foundation, and the integrity of the system. But friendship and trust also matter. There is no easy answer — both values are real.",
     ["Who is harmed when someone cheats — other than the cheater?", "Is loyalty to a friend always the right thing?", "What might happen to your friend in the long term if the cheating continues?"],
     ["What if you confronted your friend directly rather than telling anyone?", "If they were caught later and it came out you knew, how would you feel?"],
     "ethics,cheating,loyalty,integrity"),

    ("🪞 Self-Awareness", "Builders", "medium", "reflection",
     "What is a belief you held confidently one or two years ago that you have since changed your mind about? What changed it?",
     "", "Think about big or small things — values, opinions, facts, ideas about people.",
     "Changing your mind when you encounter new evidence or perspectives is a sign of maturity and intellectual honesty. The interesting part is tracing WHAT caused the shift.",
     ["Why do some people never change their minds?", "What is the difference between being open-minded and being a pushover?", "Can two people look at the same evidence and come to different conclusions honestly?"],
     ["What is something you still believe strongly today that you might change your mind about in a few years?", "Who in your life has helped you see things differently?"],
     "self-awareness,growth,open-mindedness,reflection"),

    ("💰 Financial Literacy", "Builders", "medium", "scenario",
     "You start a small business selling handmade bookmarks at school for ₹10 each. After the first week you have sold 5 and spent ₹80 on materials. Are you profitable? What do you do next?",
     "", "Think about the numbers first — income vs cost. Then think about what the numbers tell you.",
     "₹50 revenue minus ₹80 cost = -₹30 loss. You need to either charge more, reduce costs, or sell more. Week 1 losses are common in new businesses. The question is whether the model can work at scale.",
     ["What is profit?", "At what point does it make sense to keep going vs stop?", "What could you change to make it profitable?"],
     ["What if you raised the price to ₹20 — would you sell as many?", "What is one thing you could do to lower your material costs?"],
     "financial literacy,entrepreneurship,profit,business basics"),

    ("🌍 Environment & Society", "Builders", "hard", "debate_starter",
     "Rich countries cause the most pollution, but poorer countries suffer the worst consequences. Is that fair? What should be done?",
     "", "Think about who has the power to change things and who has already been harmed.",
     "This is a genuine injustice. Wealthy nations industrialised first and built prosperity on emissions. Now they ask developing nations to 'develop cleanly', which is more expensive. Responsibility and capability are distributed very unequally.",
     ["What is 'climate justice'?", "What does a wealthy country owe a poor country affected by climate change?", "Can a country have the right to develop even if it causes environmental harm?"],
     ["What would a fair international climate agreement look like?", "What can young people in wealthy countries do about this specifically?"],
     "environment,justice,inequality,global thinking"),

    ("🧠 Critical Thinking", "Builders", "hard", "scenario",
     "A viral post claims that a popular food causes illness. Everyone at school is panicking. How do you decide what is true before repeating it?",
     "", "Think about what makes a health claim credible versus alarming but unverified.",
     "Check the source: is it a peer-reviewed study or a social media post? Look for who benefits from spreading the claim. Check if reputable health organisations have said anything. 'I do not know yet' is a valid and honest answer.",
     ["What makes a health claim credible?", "Why do scary stories spread faster than corrections?", "What harm can come from repeating unverified health claims?"],
     ["What if multiple posts all said the same thing — would that make it more credible?", "What would you say to a friend who is panicking about it?"],
     "critical thinking,misinformation,health,media literacy"),

    ("❤️ Emotional Intelligence", "Builders", "hard", "scenario",
     "A friend has become increasingly negative — always complaining and bringing down the mood. You care about them but it is draining you. How do you handle this?",
     "", "Think about the difference between being a good friend and sacrificing your own wellbeing.",
     "Good friendship includes honesty: 'I notice you have been going through a hard time — I want to support you, but I also need to be honest that the negativity is affecting me.' That is kinder than quietly withdrawing.",
     ["What is the difference between supporting a friend and becoming their emotional dumping ground?", "Is it selfish to protect your own mental energy?", "How do you tell if someone needs professional support beyond what a friend can give?"],
     ["What if being honest made the friendship worse?", "What if YOU were the person being negative without realising it?"],
     "emotional intelligence,friendship,boundaries,wellbeing"),

    ("💬 Communication", "Builders", "medium", "reflection",
     "Think of a time when what you MEANT to say and what came out were completely different. What happened, and how did you repair it?",
     "", "Think about the gap between your intention and the impact on the other person.",
     "This gap is real and common. Tone, word choice, timing, and context all change how a message lands. Noticing this gap and repairing it ('What I meant was…') is a key communication skill.",
     ["Why does the same sentence mean different things to different people?", "What role does tone play in how a message is received?", "Is the intention or the impact more important?"],
     ["How did the other person react?", "What could you have said instead to make your intention clearer?"],
     "communication,intention vs impact,reflection,repair"),

    ("🤝 Social Skills & Teamwork", "Builders", "hard", "scenario",
     "You are in a WhatsApp group and someone sends a mocking message about a classmate. Most people laugh along. What do you do?",
     "", "Think about what silence in a group chat communicates. And what speaking up costs versus gains.",
     "Laughing along = participation. Silence = implicit approval. Leaving the chat = dramatic. Saying 'This is mean, let's not' is hard but it changes the group's understanding of what is acceptable.",
     ["What is mob mentality and why do people go along with group behaviour?", "Is online cruelty different from face-to-face cruelty?", "What happens to your own character when you stay silent about something wrong?"],
     ["What if it was your close friend who sent the message?", "What if the person it was about was in the group?"],
     "cyberbullying,peer pressure,courage,social media"),

    ("🏆 Leadership & Decisions", "Builders", "hard", "what_if",
     "What if your school gave students — not teachers — the power to set all classroom rules for one month? What rules would you create and why?",
     "", "Think about what rules would actually make things better — not just more fun.",
     "Strong answers balance student needs with learning goals. Rules that only benefit students at the cost of learning are not good governance. This exercise also reveals why rule-making is harder than it looks.",
     ["Why do schools have rules in the first place?", "What rules would you definitely keep?", "What happens when a rule is unfair to some students but fair to others?"],
     ["What is one rule you would make that no adult has thought of?", "After the month ends, which rules do you think should stay permanent?"],
     "leadership,governance,rules,decision making"),

    ("🎨 Creativity & Problem Solving", "Builders", "hard", "creative",
     "Design a city of the future where nobody feels lonely. What would it look like? What systems would make people feel connected?",
     "", "Think about what actually causes loneliness — and what makes people genuinely feel part of something.",
     "Physical design (shared spaces, walkable streets) matters less than social systems (reasons to gather, knowing your neighbours, purpose). The best answers address structure AND human behaviour.",
     ["What causes loneliness in cities today?", "Is it possible to design away loneliness?", "What is the difference between being alone and being lonely?"],
     ["Would introverts want to live in your city?", "What could we change about where you live now to make it less lonely?"],
     "creativity,urban design,social connection,empathy"),

    ("⚖️ Ethics & Values", "Builders", "medium", "scenario",
     "A shopkeeper gives you ₹50 too much in change by mistake. You only realise when you are outside. Do you go back?",
     "", "Think about convenience vs honesty. What would you think of yourself if you did not go back?",
     "Going back is right, even if inconvenient. The shopkeeper will likely be short at the end of the day and may not know why. Honesty in small moments — when you could easily get away with something — defines character.",
     ["Does the amount of money matter — would your answer change if it were ₹5 vs ₹500?", "What is integrity?", "How does this small decision reflect on who you are?"],
     ["What if you were in a real hurry?", "What if you had no money that day and really needed it?"],
     "honesty,integrity,ethics,everyday decisions"),

    ("🪞 Self-Awareness", "Builders", "hard", "reflection",
     "What is one thing about yourself that you find genuinely hard to admit — even privately? You do not have to share it. Just think about WHY it is hard to admit.",
     "", "Think about what admitting it to yourself would mean or cost.",
     "This question is deliberately private. The value is in the thinking, not the sharing. Hard-to-admit truths are usually about ways we have fallen short of our own values — and that discomfort is called conscience.",
     ["Why is it sometimes harder to be honest with yourself than with others?", "What is the difference between self-criticism and self-awareness?", "Does acknowledging a flaw make it better or worse?"],
     ["What would change if you fully accepted this truth about yourself?", "What is the difference between shame and guilt — and which is more useful?"],
     "self-awareness,honesty,growth,reflection"),

    ("💰 Financial Literacy", "Builders", "hard", "debate_starter",
     "Should pocket money be given freely each week or only earned through doing chores? What does each approach teach children about money?",
     "", "Think about what message each approach sends about the relationship between work and reward.",
     "Earned money teaches labour-value linkage. Free allowance teaches budgeting and responsibility without tying affection/resources to performance. Both have real merits and real drawbacks — the best approach may be a mix.",
     ["What does money represent in your family?", "Is it problematic to pay children for tasks that should be done as family responsibilities?", "What do adults get paid for — and how does that compare?"],
     ["What if a child had a disability that limited what chores they could do — should they get less?", "What values do you want children to learn about money?"],
     "financial literacy,debate,chores,values"),

    ("🌍 Environment & Society", "Builders", "medium", "creative",
     "Design one product using items found at home that solves a small but real environmental problem. Describe it and explain how it works.",
     "", "Think about problems you notice every day at home. Small and practical beats big and impossible.",
     "Strong answers target a specific problem (food waste, plastic use, water waste) with a realistic solution. The design thinking process: problem → constraints → solution → test.",
     ["What environmental problems do you notice at home?", "What resources do you already have that are wasted?", "How would you test if your product actually works?"],
     ["Could this product be made cheaply enough for others to use?", "What happens to your product at the end of its life?"],
     "environment,design thinking,creativity,sustainability"),

    # ══════════════════════════════════════════════════════════════════════════
    # CHALLENGERS  (14-16)  — 20 questions
    # ══════════════════════════════════════════════════════════════════════════

    ("🧠 Critical Thinking", "Challengers", "hard", "debate_starter",
     "Artificial intelligence can now write essays and do homework for students. Should schools allow it? What changes if they do?",
     "", "Think about what education is FOR — and whether AI changes the answer.",
     "If the purpose of education is to develop thinking, allowing AI to think on your behalf defeats the goal. If the purpose is demonstrating knowledge, it raises questions about what we are measuring and why.",
     ["What is the actual purpose of homework?", "How do we know what a student knows if AI writes their work?", "What happens to skills we stop practising because AI does them?"],
     ["What is one thing AI genuinely should be allowed to help students with?", "How should schools respond to AI tools rather than just banning them?"],
     "AI,education,critical thinking,technology"),

    ("❤️ Emotional Intelligence", "Challengers", "hard", "scenario",
     "Someone you genuinely dislike comes to you clearly distressed and needing help. Do you help them — and does your personal feeling change what is right?",
     "", "Separate what you feel from what you believe is right. Can you act against your feeling?",
     "What is right (helping someone in distress) does not depend on your personal feelings. You can choose to help even while disliking them. That distinction — between feeling and ethics — is emotional and moral maturity.",
     ["Does someone have to earn your help?", "What would you think of yourself if you walked away?", "Could helping actually change how you feel about the person?"],
     ["What is the minimum you would be willing to do in this situation?", "What if helping them cost you something real?"],
     "emotional intelligence,empathy,ethics,character"),

    ("💬 Communication", "Challengers", "hard", "reflection",
     "Think of a conversation you wish you had handled very differently. What would you say now — and what was stopping you from saying it then?",
     "", "Think about the fear or habit that blocked the better response.",
     "Most people have these. The gap between what we wish we had said and what we said reveals our communication limits at that moment. Understanding why we froze or responded poorly is the first step to doing better.",
     ["What emotions get in the way of saying what we really mean?", "How does fear shape what we say and do not say?", "Is it ever too late to have a conversation you wished you had?"],
     ["Could you have that conversation now — even belatedly?", "What has changed in you since then that would allow you to handle it better?"],
     "communication,reflection,courage,regret"),

    ("🤝 Social Skills & Teamwork", "Challengers", "hard", "dilemma",
     "You discover a close friend has been spreading false rumours about you behind your back. How do you confront them — or do you at all?",
     "", "Think about what you want the outcome to be before deciding how to act.",
     "Confronting directly (privately, calmly, with 'I' statements) gives the friendship a chance to survive — and is honest. Ignoring it silently destroys trust anyway. Knowing what you want (closure? apology? explanation?) shapes your approach.",
     ["Why might someone spread rumours about a friend?", "What is the difference between a confrontation and a conversation?", "What do you need from this person in order to repair the friendship?"],
     ["What if they denied it when you confronted them?", "Is a friendship where this has happened worth saving?"],
     "friendship,conflict,trust,confrontation"),

    ("🏆 Leadership & Decisions", "Challengers", "hard", "scenario",
     "Three weeks into a group project, your team is falling apart — tension, missed deadlines, disengagement. What do you do as leader?",
     "You are asked to lead but have no formal authority to enforce anything.", "Think about what is causing the breakdown before trying to fix it.",
     "Diagnosis before prescription: a team breaks down because of unclear roles, poor communication, conflicting priorities, or unresolved tension. Reset the expectations, have honest conversations, redistribute work, re-establish the goal.",
     ["How do you rebuild trust once it has broken down?", "What is the difference between a leader who commands and one who facilitates?", "What can you do that the team cannot do without you?"],
     ["What if the breakdown is partly your own fault?", "What does a team need to recover from setbacks — practically and emotionally?"],
     "leadership,team dynamics,conflict resolution,resilience"),

    ("🎨 Creativity & Problem Solving", "Challengers", "hard", "creative",
     "Create a brief TEDx talk outline — title and five key ideas — on a problem that matters deeply to your generation.",
     "", "Think about what you actually care about. What do adults not understand that you do?",
     "The best talks come from genuine conviction and specific insight, not generic topics. Pick something you know from experience. Five ideas should build on each other — not just be a list.",
     ["What is a problem your generation understands better than older generations?", "What makes a talk persuasive vs just interesting?", "What do you know that most people do not?"],
     ["What story from your own life could you open the talk with?", "What is the one thing you want the audience to do or think after your talk?"],
     "creativity,public speaking,ideas,generation"),

    ("⚖️ Ethics & Values", "Challengers", "hard", "what_if",
     "You discover that something your family does regularly — a food you eat, a product you use — causes serious harm to others or the environment. What do you do?",
     "", "Think about the difference between knowing something is wrong and acting on that knowledge.",
     "This question tests the gap between belief and action. Raising it with your family is hard. Changing your own behaviour is easier. But the question is about moral responsibility when you know — and what knowing obligates you to.",
     ["Is there a moral difference between knowing and not knowing?", "What makes it hard to act on your values when family habits are involved?", "What is the responsibility of the individual vs the company that makes the product?"],
     ["What if your family dismissed your concern?", "What is one thing you could do — even small — that is consistent with this knowledge?"],
     "ethics,values,family,environmental impact"),

    ("🪞 Self-Awareness", "Challengers", "hard", "reflection",
     "What is one thing you are actively avoiding in your life right now? What do you think would happen if you stopped avoiding it?",
     "", "Be specific — not 'hard work' in general, but a particular thing you keep putting off.",
     "Avoidance always has a reason: fear, shame, uncertainty, difficulty. The thing being avoided rarely goes away — it usually grows. Understanding WHY you avoid is more valuable than just pushing through.",
     ["What is the cost of continued avoidance?", "Is there a difference between choosing not to do something and avoiding it?", "What would you advise a friend in the same situation?"],
     ["What is the first smallest step you could take toward it?", "How long have you been avoiding it?"],
     "self-awareness,avoidance,courage,reflection"),

    ("💰 Financial Literacy", "Challengers", "hard", "scenario",
     "You and a close friend start a small business. After three months it is profitable. You want to reinvest; they want to split the money now. How do you resolve this disagreement?",
     "", "Think about what each approach does to the business and the friendship long-term.",
     "This is a real business and relationship tension. The key is separating the business decision from the personal one — and having a structure (partnership agreement) before it becomes a crisis. Communication, data, and compromise all matter.",
     ["What are the arguments for each approach?", "Should a business partnership be structured like a friendship or like a contract?", "What would a business advisor say?"],
     ["What if you absolutely could not agree — what options do you have?", "What would you put in writing before starting a business with a friend in the future?"],
     "financial literacy,entrepreneurship,partnerships,conflict"),

    ("🌍 Environment & Society", "Challengers", "hard", "scenario",
     "Your city proposes cutting down a forest to build a tech campus that will create 5,000 new jobs. Do you support or oppose it — and how do you weigh the trade-offs?",
     "", "Think about who benefits and who bears the cost — and whether those are the same people.",
     "Jobs vs environment is a genuine trade-off. The question is whether it is presented as binary when it is not. Could the campus be built elsewhere? Could it be a smaller footprint? Who in the city needs those jobs most?",
     ["Who are the stakeholders in this decision?", "What does 'short-term gain vs long-term cost' mean in this context?", "Is economic development always worth environmental cost?"],
     ["What questions would you need answered before making a final decision?", "How would you make your voice heard in this decision?"],
     "environment,trade-offs,urban development,civic engagement"),

    ("🧠 Critical Thinking", "Challengers", "hard", "scenario",
     "A classmate argues passionately for a policy using many statistics. You feel uneasy but cannot immediately find the flaw. What do you do?",
     "", "Think about why feeling uneasy might be a signal worth following — not a weakness.",
     "Intuitive discomfort often points to something real even before you can articulate it. You can say 'I am not sure I agree but I want to think about it more' — that is honest and intelligent. Demanding to see the full source of statistics is fair.",
     ["Is emotional discomfort a valid reason to doubt an argument?", "What questions can you ask to probe the strength of statistics?", "Why do statistics sometimes mislead even when they are technically correct?"],
     ["What if the person was very confident and well-spoken — would that change how you felt?", "How do you disagree with someone publicly when you do not yet have a counter-argument?"],
     "critical thinking,statistics,debate,intellectual humility"),

    ("❤️ Emotional Intelligence", "Challengers", "hard", "reflection",
     "Describe a situation where you were angry at someone — and later realised the anger was really about yourself. What does that pattern reveal?",
     "", "Think about misdirected emotion — when we blame others for feelings that belong to us.",
     "Projection — directing internal feelings outward — is extremely common. Understanding when your anger is really self-directed (guilt, shame, frustration at your own limits) takes considerable self-awareness.",
     ["Why is it easier to be angry at someone else than at yourself?", "What triggers the kind of anger that is really self-directed?", "What happened after you realised the truth — did you apologise?"],
     ["What would it take to recognise this pattern IN the moment rather than after?", "Is there a current situation where something similar might be happening?"],
     "emotional intelligence,projection,self-awareness,anger"),

    ("💬 Communication", "Challengers", "hard", "debate_starter",
     "When honesty and kindness conflict — which matters more? Give a specific real-world example to defend your position.",
     "", "Think about who gets to decide what is 'kind' and what is 'honest' in that moment.",
     "The binary is partly false: honest delivery matters enormously. But sometimes the kindest thing is uncomfortable truth. The better question is: honest to whom, about what, and for whose benefit?",
     ["Can you be honest AND kind at the same time?", "Who benefits when we withhold the truth 'to be kind'?", "Is it ever truly kind to deceive someone?"],
     ["Give an example of honesty that was unkind — what made it unkind?", "Give an example of kindness that was dishonest — what were the long-term consequences?"],
     "communication,honesty,kindness,ethics"),

    ("🤝 Social Skills & Teamwork", "Challengers", "hard", "what_if",
     "What if your school ran on a visible reputation score — every action you took was rated and displayed publicly? How would it change behaviour?",
     "", "Think about which behaviours would increase and which would decrease — and what that says about human nature.",
     "Positive: people would behave better publicly. Negative: the performance of virtue without real virtue, loss of privacy, gaming the system. China's social credit system is a real-world version of this — and it is controversial.",
     ["What behaviour would change under a reputation system?", "Is there a difference between being good and appearing good?", "Who decides what counts as good behaviour in this system?"],
     ["What would you do privately that you would not do with a score attached?", "Is privacy necessary for authentic behaviour?"],
     "social systems,privacy,ethics,behaviour,peer pressure"),

    ("🏆 Leadership & Decisions", "Challengers", "hard", "reflection",
     "Think of a time you followed the crowd even though you privately disagreed. Why did you go along — and what would it have taken to speak up?",
     "", "Think about the cost of speaking up versus the cost of staying silent.",
     "Conformity pressure is powerful and real. Understanding exactly what stopped you — social fear, effort, uncertainty about your own judgement — is the first step to building the muscle of speaking up.",
     ["What is the cost of going along with things you disagree with over time?", "What is the difference between being open-minded and being a pushover?", "When is conformity a rational choice rather than a moral failure?"],
     ["What would you need to feel safe enough to speak up in that kind of situation?", "Can you think of a time you DID speak up against the group? What happened?"],
     "leadership,conformity,courage,peer pressure,integrity"),

    ("🎨 Creativity & Problem Solving", "Challengers", "hard", "what_if",
     "What if failure was celebrated in schools the same way that success is? How would education be different?",
     "", "Think about what people actually learn from failure — and what the fear of failure costs us.",
     "Fear of failure suppresses risk-taking, creativity, and honest questioning. A culture that treats failure as data rather than shame would produce more experimentation, resilience, and genuine understanding.",
     ["What do you currently sacrifice to avoid failure or looking foolish?", "What is the most valuable thing you have ever learned from failing?", "What stops schools from implementing this?"],
     ["What would your grade report look like in a school that valued failure?", "What subject would you tackle differently if you knew failure was celebrated?"],
     "creativity,education,failure,growth mindset"),

    ("⚖️ Ethics & Values", "Challengers", "hard", "dilemma",
     "You know a secret that, if revealed, would seriously hurt someone you love — but keeping it is also causing harm to others. What do you do?",
     "This is not hypothetical — imagine a specific situation that feels real.", "Think about proportionality: how much harm on each side? Who is harmed? Are they able to protect themselves?",
     "There is no clean answer. The key variables: severity of harm, whether you are the only one who knows, whether the affected party can protect themselves, and your relationship to both parties. Silence is also a choice with consequences.",
     ["Is there someone you could consult confidentially?", "What is your responsibility to people outside your immediate circle?", "What would you think of yourself in ten years depending on the choice you made?"],
     ["What if you gave the person with the secret a deadline to tell the truth themselves?", "Who else shares the moral burden in this situation?"],
     "ethics,secrets,harm,loyalty,moral dilemma"),

    ("🪞 Self-Awareness", "Challengers", "hard", "reflection",
     "What is the gap between who you are today and who you want to be in five years? What specifically is standing between you and that version of yourself?",
     "", "Be concrete — not 'I want to be better', but what specific traits and habits.",
     "Clarity about the gap is the precondition for change. Most people either do not know who they want to be, or know but cannot name what blocks them. Both the vision and the obstacle need to be specific.",
     ["What does the five-year version of you do differently — in habits, relationships, choices?", "What is the single biggest obstacle?", "Is the obstacle internal (mindset, habits) or external (circumstances)?"],
     ["What is one thing you could start today?", "Who do you know who is already closer to who you want to be — what can you learn from them?"],
     "self-awareness,growth,goals,identity"),

    ("💰 Financial Literacy", "Challengers", "hard", "debate_starter",
     "Universal basic income — a fixed monthly payment to every citizen regardless of employment — is being tested globally. Would it work? What are the real risks?",
     "", "Think about incentives, funding, and what money actually does to motivation.",
     "Proponents: reduces poverty, enables risk-taking, recognises unpaid labour. Critics: reduces work incentive, inflation risk, expensive. Evidence from trials is mixed and context-dependent. The question is nuanced.",
     ["How would a universal basic income be funded?", "Would it reduce the motivation to work?", "Who would benefit most and least from this policy?"],
     ["What problem is UBI trying to solve — and are there better ways to solve it?", "Would you want to live in a country with UBI?"],
     "financial literacy,economics,UBI,policy,debate"),

    ("🌍 Environment & Society", "Challengers", "hard", "debate_starter",
     "Should teenagers have the right to vote on climate policies that will directly affect their generation far more than adults? Argue both sides.",
     "", "Think about what voting rights are based on — age, maturity, stake, or something else?",
     "For: teenagers have the highest stake, are often better informed on climate. Against: cognitive development, easily influenced, existing rights structures. The deeper question: what is the basis for democratic participation?",
     ["What is the current basis for setting the voting age?", "Are teenagers more or less informed on climate issues than average adults?", "What happens to political decisions when the most affected group has no vote?"],
     ["What age would you set the voting age at — for climate policy specifically?", "Should there be other issue-specific votes where the stake-holders are defined differently?"],
     "environment,voting rights,democracy,climate,debate"),

    # ══════════════════════════════════════════════════════════════════════════
    # LEADERS  (17-18)  — 20 questions
    # ══════════════════════════════════════════════════════════════════════════

    ("🧠 Critical Thinking", "Leaders", "hard", "debate_starter",
     "Democracy assumes citizens will make informed decisions. In an age of misinformation and algorithmic bubbles, is that assumption still valid?",
     "", "Think about whether the problem is the system or the information environment around it.",
     "Democracy has always coexisted with imperfect information. But algorithmic amplification of emotionally engaging content, filter bubbles, and deliberate disinformation are qualitatively different challenges. Reform, media literacy, and institutional design are all partial answers.",
     ["What does a functioning democracy actually require from citizens?", "Is the answer to fix the information environment or redesign the democratic process?", "What countries have tried effective responses to misinformation?"],
     ["What responsibility do you personally have as a voter in this environment?", "If you could redesign how information reaches voters, what would you change?"],
     "democracy,critical thinking,misinformation,media literacy"),

    ("❤️ Emotional Intelligence", "Leaders", "hard", "reflection",
     "Think of someone you found very hard to forgive. What specifically made forgiveness difficult — and is forgiveness always necessary for your own peace?",
     "", "Think about what forgiveness is and is not. It is not the same as condoning or reconciling.",
     "Forgiveness is not about the other person — it is about releasing the grip of the injury on you. But it is also not always available on demand, and forcing it can be its own form of self-betrayal. This is complex and personal.",
     ["What is the difference between forgiving and forgetting?", "What is the difference between forgiving and reconciling?", "What happens to you emotionally when you cannot let go of an injury?"],
     ["Has the person you were thinking of made it easy or hard to forgive — and why does that matter?", "Is there a form of acceptance that is not quite forgiveness but is still freeing?"],
     "forgiveness,emotional intelligence,trauma,healing"),

    ("💬 Communication", "Leaders", "hard", "scenario",
     "You are giving a high-stakes presentation when someone in the audience begins aggressively challenging every point you make. How do you respond?",
     "", "Think about staying grounded under pressure. What does composure actually look like in practice?",
     "Acknowledge the challenge ('That is a fair question/challenge'), answer what you can, admit uncertainty where you have it, and do not get drawn into emotional escalation. Confidence does not require destroying the challenger.",
     ["What does it look like to stay calm and credible under pressure?", "What is the difference between defending your position and being defensive?", "How do you handle a challenge you genuinely cannot answer in the moment?"],
     ["What if the challenger was factually wrong — how do you correct them without humiliating them?", "What preparation would have helped you handle this situation better?"],
     "communication,public speaking,pressure,composure"),

    ("🤝 Social Skills & Teamwork", "Leaders", "hard", "dilemma",
     "A mentor who helped you greatly has done something you consider genuinely unethical. Do you speak up — and if so, how?",
     "", "Think about the complexity of owing gratitude while also holding standards.",
     "Gratitude does not require endorsement of wrongdoing. Speaking up respectfully ('I care about you and I have to be honest about this') respects both the relationship and your values. Silence for the sake of gratitude can become complicity.",
     ["Does what someone has done for you obligate you to overlook what they do wrong?", "What is the difference between loyalty and complicity?", "How do power and dependency affect our willingness to speak up?"],
     ["What if speaking up damaged your relationship with them permanently?", "What would you think of yourself in ten years depending on whether you spoke up?"],
     "mentorship,ethics,loyalty,courage,speaking up"),

    ("🏆 Leadership & Decisions", "Leaders", "hard", "scenario",
     "You are appointed to lead a diverse team on a high-stakes project. Members have different working styles, backgrounds, and priorities. How do you build trust quickly?",
     "", "Think about what trust actually is and what creates it — not just good intentions.",
     "Trust is built through consistency, clarity, and genuine interest in the people you lead. Early actions: listen first, be transparent about constraints, involve the team in decisions where possible, and be reliable on small things before large ones.",
     ["What destroys trust fastest in a new team?", "How do you lead people who are more experienced than you in their domain?", "What is the first thing you would do in week one?"],
     ["How do you manage someone who does not trust you from the start?", "What have you observed about what trust looks like in teams you have been part of?"],
     "leadership,trust,team building,diversity"),

    ("🎨 Creativity & Problem Solving", "Leaders", "hard", "creative",
     "You have unlimited budget and full government support to redesign the Indian education system. What are your first three changes and why?",
     "", "Think about root causes, not symptoms. What does the system need that it currently lacks?",
     "Strong answers diagnose the system: rote learning over thinking, teacher quality and conditions, equity gaps, relevance to the economy. Each change should explain what it solves and how it is implemented, not just what it is.",
     ["What does the current system do well?", "What is the single biggest failure of the current system?", "Who are the most important stakeholders to bring on board?"],
     ["What would you measure to know if your changes were working?", "Which country's education system would you draw the most from?"],
     "creativity,education,policy,India,design thinking"),

    ("⚖️ Ethics & Values", "Leaders", "hard", "what_if",
     "What if a pill guaranteed you would always make the ethically right decision — but required removing your emotions completely? Would you take it?",
     "", "Think about what role emotions play in moral reasoning — are they noise or signal?",
     "Emotions are not obstacles to ethics — they are often inputs. Empathy, guilt, and love point toward moral truths. A purely rational ethics without emotions might be precise but would miss human complexity. Trolley-problem thinking has limits.",
     ["What role do emotions play in your ethical decisions?", "Is pure rationality enough to make good moral decisions?", "What would you lose if you could not feel guilt, love, or empathy?"],
     ["What kinds of ethical decisions would be better without emotions?", "What kinds would be worse?"],
     "ethics,emotions,moral philosophy,decision making"),

    ("🪞 Self-Awareness", "Leaders", "hard", "reflection",
     "What assumptions do you carry about people very different from you — in religion, class, or political view? Where did those assumptions come from?",
     "", "Be honest. We all carry assumptions. The question is whether we can trace them.",
     "Assumptions often come from family, media, and limited exposure. The first step to examining bias is acknowledging that everyone has it — including thoughtful people. Tracing the source helps decide whether the assumption is earned or inherited.",
     ["What is the difference between a stereotype and a generalisation?", "Can assumptions be accurate and still be harmful?", "When did you last have an assumption challenged by direct experience?"],
     ["What is one assumption you hold that you would like to test?", "How would you go about doing that?"],
     "self-awareness,bias,assumptions,empathy"),

    ("💰 Financial Literacy", "Leaders", "hard", "scenario",
     "You are 22 and have received ₹10 lakh unexpectedly. You have student loans, a business idea, and parents who want you to invest in property. How do you decide?",
     "", "Think about risk, return, obligation, and your own life priorities — not just what is financially optimal.",
     "This is a real decision with competing pressures. Emergency fund first. Then: loan interest vs investment return, risk tolerance, opportunity cost of the business idea, family obligation vs personal autonomy. There is no universal right answer.",
     ["What is the cost of carrying student debt versus the cost of not investing?", "How do you weigh family expectation against your own judgement?", "What would you regret more in ten years?"],
     ["Who would you consult before deciding?", "What does this decision reveal about your values and priorities?"],
     "financial literacy,personal finance,decisions,independence"),

    ("🌍 Environment & Society", "Leaders", "hard", "what_if",
     "What if fossil fuels ran out completely tomorrow? Walk through what happens in the first 24 hours, one month, and five years.",
     "", "Think systematically — energy connects to everything: food, water, transport, industry, warmth.",
     "Hour 1: blackouts, transport freezes, hospitals on backup power. Month 1: food supply collapse, civil unrest, rapid renewable build-out attempts. Year 5: rebuilt infrastructure around alternatives but with massive inequality in who survived the transition.",
     ["What systems are most dependent on fossil fuels?", "Which populations would suffer most in the transition?", "What technology already exists that could scale fastest?"],
     ["What is the difference between a sudden end and a managed transition?", "What does this thought experiment tell us about urgency on climate change today?"],
     "environment,systems thinking,energy,consequences"),

    ("🧠 Critical Thinking", "Leaders", "hard", "reflection",
     "State a belief you hold very strongly. Now argue the opposite as convincingly as you can. Does the exercise change anything for you?",
     "", "Take a genuine belief — not a safe topic you do not really care about.",
     "The ability to steelman an opposing view is one of the most valuable intellectual skills. It does not mean abandoning your view. It means you understand it well enough to know why people disagree — and can engage with that honestly.",
     ["What is the difference between steelmanning and being persuaded?", "What did you learn about your own belief by arguing against it?", "What makes some people unable or unwilling to do this exercise?"],
     ["What is one point from the opposite argument that you actually find compelling?", "How does this exercise apply to politics, religion, or deeply personal values?"],
     "critical thinking,intellectual humility,steelmanning,debate"),

    ("❤️ Emotional Intelligence", "Leaders", "hard", "dilemma",
     "A colleague on your team is struggling with mental health issues that are affecting their work. You are their peer, not their manager. What is your responsibility — and where is the limit?",
     "", "Think about the difference between care and overreach. And about your own limits.",
     "Peer responsibility: express care, offer practical support, mention professional resources. You cannot be their therapist. Taking on too much harms both of you. The distinction between 'I am here for you' and 'I will fix this' matters enormously.",
     ["What can a peer realistically offer that a manager or professional cannot?", "What is the risk of taking on too much responsibility for someone else's mental health?", "How do you bring it up without making them feel labelled or pressured?"],
     ["What would you do if your concern was ignored?", "What resources does your school or workplace have that you could point them toward?"],
     "emotional intelligence,mental health,peer support,boundaries"),

    ("💬 Communication", "Leaders", "hard", "what_if",
     "What if every person was required to live in a completely different culture for 30 days every five years? How would it change human communication and understanding?",
     "", "Think about what exposure does and does not do to prejudice and understanding.",
     "Exposure reduces some prejudice but not all — it depends on the quality of the interaction. However, even imperfect exposure builds complexity in how we see 'others'. The requirement would also raise freedom vs mandate questions.",
     ["Does exposure to difference automatically create understanding?", "What conditions are needed for exposure to actually reduce prejudice?", "What would be the economic and political challenges of this policy?"],
     ["What would you personally get from 30 days in a culture very different from your own?", "What culture would you choose — and what do you think it would teach you?"],
     "communication,empathy,culture,global thinking"),

    ("🤝 Social Skills & Teamwork", "Leaders", "hard", "debate_starter",
     "Psychologists argue that online friendships are not as real or meaningful as in-person ones. Do you agree — and what makes a relationship real?",
     "", "Think about what qualities define a meaningful relationship — and whether medium matters.",
     "Depth, consistency, mutual support, vulnerability — these define a real relationship. Medium matters less than quality. Online relationships can have all of these. But proximity enables certain forms of support that distance prevents.",
     ["What does a friendship need to be 'real'?", "What can online relationships do well? What do they do poorly?", "Has an online relationship ever been more meaningful to you than a physical one?"],
     ["How has your relationship with social media changed over the past few years?", "What is something you share online that you would never share in person — and why?"],
     "relationships,social media,friendship,authenticity"),

    ("🏆 Leadership & Decisions", "Leaders", "hard", "dilemma",
     "For a promotion, you must choose between two candidates: one is more technically skilled but difficult to work with; the other is less skilled but excellent for team culture. Who do you choose?",
     "", "Think about what the role actually requires and what the team needs right now.",
     "Neither is universally right. Technical skill matters more in some roles; cultural fit matters more in teams that are struggling or growing fast. The real question is: can the skill gap be closed? Can the attitude problem be coached?",
     ["What does the team need most in this moment?", "Can you develop skill faster than you can change attitude?", "What happens to the other person — do they have a future with the team?"],
     ["How do you tell the person you did not choose?", "Would your answer change if the technically skilled person was aware of their difficulty and actively working on it?"],
     "leadership,hiring,decisions,team culture"),

    ("🎨 Creativity & Problem Solving", "Leaders", "hard", "what_if",
     "What if every person on Earth had access to exactly the same quality of education from birth? How would the world look different in 50 years?",
     "", "Think about second and third-order effects — not just 'everyone would be smarter'.",
     "More equal economic mobility. Disruption of inherited power structures. Increased innovation. But also: equal access does not equal equal outcome — culture, motivation, and support still vary. And what does 'same quality' even mean across contexts?",
     ["What drives inequality beyond education?", "What would be gained — and what would be lost — from a more equal world?", "What would this mean for the current global elite?"],
     ["What would your own life look like differently?", "What systems keep education unequal today — beyond just money?"],
     "education,inequality,global thinking,imagination"),

    ("⚖️ Ethics & Values", "Leaders", "hard", "scenario",
     "You are offered a high-paying job at a company with excellent benefits, but the company has a documented poor environmental and labour record. You need the income. What do you do?",
     "", "Think about what you can and cannot control once you are inside a system.",
     "Working within a flawed system vs refusing it are both morally complex. Inside, you have potential influence and income. Outside, you maintain clean hands but less impact. The question is whether individual participation changes the institution — or normalises it.",
     ["What is the difference between complicity and pragmatism?", "Can you change an institution from within?", "What would have to be true for you to say yes despite the company's record?"],
     ["What if every company in your field had a poor record — would that change your answer?", "What would you try to change if you did take the job?"],
     "ethics,career,complicity,values,trade-offs"),

    ("🪞 Self-Awareness", "Leaders", "hard", "reflection",
     "What recurring pattern do you notice across your important relationships — friendships, family, or romantic? What role do YOU play in that pattern?",
     "", "Think honestly about what you bring to your relationships — not just what others do.",
     "Patterns repeat because we bring the same tendencies to new relationships. Noticing your own role — people-pleasing, withdrawing when hurt, seeking control — is the hardest and most important insight. Changing the pattern means changing yourself first.",
     ["What is the earliest version of this pattern you can remember?", "Who in your family shows a similar pattern?", "What would a relationship look like that broke this pattern?"],
     ["What is one thing you could do differently in your next important relationship conflict?", "Who do you trust enough to get honest feedback from about this?"],
     "self-awareness,relationships,patterns,growth"),

    ("💰 Financial Literacy", "Leaders", "hard", "reflection",
     "What is your current emotional relationship with money — anxiety, indifference, excitement? Where did that attitude come from — and does it serve you?",
     "", "Think about the stories you absorbed about money growing up, not just what you were taught explicitly.",
     "Money attitudes are largely inherited from family culture and early experience: scarcity, shame, status, or freedom. Recognising your emotional default helps you make more rational decisions instead of reactive ones.",
     ["What did your family communicate about money — explicitly and implicitly?", "In what way might your current attitude be helping you? Hurting you?", "What would a healthy relationship with money look like to you?"],
     ["What is one financial decision you made recently that was more emotional than rational?", "Who in your life has a relationship with money you admire — and what is different about it?"],
     "financial literacy,self-awareness,money mindset,reflection"),

    ("🌍 Environment & Society", "Leaders", "hard", "dilemma",
     "You are offered a high-paying role at a fossil fuel company — the only offer after months of job searching. The job would let you pay off your family's debt. What do you do?",
     "", "Think about personal obligation, systemic responsibility, and whether individual choice matters in the large picture.",
     "This pits clear personal obligation against clear ethical concern. Individual entry into an industry does not meaningfully change it. But participation normalises it and builds the industry's legitimacy. There is no clean answer — and anyone who says there is has not thought carefully.",
     ["What is owed to your family vs your values?", "Does one person taking or refusing a job affect the fossil fuel industry at all?", "What would you try to do differently once inside?"],
     ["What are you prepared to compromise on — and what is your absolute line?", "What else could you do to address your family's debt while you look for alternatives?"],
     "environment,ethics,career,dilemma,responsibility"),
]


def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Run the app first to initialise it.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # Build lookup maps
    topic_map = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM topics")}
    ag_map    = {r["label"]: r["id"] for r in conn.execute("SELECT id, label FROM age_groups")}

    # Get existing question texts to avoid duplicates
    existing = {
        r[0].strip().lower()
        for r in conn.execute("SELECT question_text FROM questions")
    }

    inserted = 0
    skipped  = 0

    for row in QUESTIONS:
        (topic, age_group, level, q_type,
         question_text, context, hint, sample_answer,
         discussion_points, follow_up_questions, tags) = row

        if question_text.strip().lower() in existing:
            skipped += 1
            continue

        if topic not in topic_map:
            print(f"  ⚠️  Unknown topic: {topic!r} — skipping")
            skipped += 1
            continue

        if age_group not in ag_map:
            print(f"  ⚠️  Unknown age group: {age_group!r} — skipping")
            skipped += 1
            continue

        conn.execute(
            """INSERT INTO questions
               (topic_id, age_group_id, level, question_type, question_text, context,
                hint, sample_answer, discussion_points, follow_up_questions, tags, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                topic_map[topic], ag_map[age_group], level, q_type,
                question_text.strip(), context.strip(), hint.strip(), sample_answer.strip(),
                json.dumps(discussion_points), json.dumps(follow_up_questions),
                tags, "seed",
            ),
        )
        existing.add(question_text.strip().lower())
        inserted += 1

    conn.commit()
    conn.close()

    print(f"\n✅  Done — {inserted} questions inserted, {skipped} skipped (already existed).")
    print(f"   Total now: run the app and check the Question Bank.")


if __name__ == "__main__":
    main()
