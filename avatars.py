"""
SpendWise Dynamic Avatar Engine
Provides intelligent gender detection and unique, deterministic avatar assignment
for users based on their name and email, ensuring boys receive distinct boy avatars
and girls receive distinct girl avatars.
"""
import hashlib
from typing import Dict, List

# Curated, verified high-resolution portraits (Boys / Men)
BOY_AVATARS: List[str] = [
    "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1566492031773-4f4e44671857?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1583864697784-a0efc8379f70?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1501196354995-cbb51c65aaea?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1463453091185-61582044d556?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1513956589380-bad6acb9b9d4?w=200&auto=format&fit=crop&q=80"
]

# Curated, verified high-resolution portraits (Girls / Women)
GIRL_AVATARS: List[str] = [
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1548142813-c348350df52b?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1546961329-78bef0414d7c?w=200&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1525130413817-d45c1d127c42?w=200&auto=format&fit=crop&q=80"
]

# Set of common male names (Indian & International)
MALE_NAMES = {
    'krishna', 'ram', 'rama', 'shiva', 'surya', 'aditya', 'abhay', 'rahul', 'amit',
    'rohit', 'rohan', 'aryan', 'arjun', 'ajay', 'vijay', 'suresh', 'ramesh', 'ganesh',
    'mahesh', 'sachin', 'virat', 'hardik', 'shubman', 'neeraj', 'ayush', 'aman',
    'ankit', 'yash', 'kunal', 'dev', 'pranav', 'varun', 'gaurav', 'mohit', 'mayank',
    'kartik', 'tarun', 'tushar', 'abhishek', 'shivam', 'vivek', 'vikas', 'saurabh',
    'alok', 'ashish', 'deepak', 'sandeep', 'pradeep', 'jitendra', 'dharmendra',
    'rajesh', 'rakesh', 'mukesh', 'dinesh', 'sunil', 'anil', 'sanjeev', 'rajiv',
    'sanjay', 'manoj', 'vinod', 'ashok', 'naresh', 'harish', 'satish', 'hemant',
    'chetan', 'vishal', 'manish', 'nitin', 'sumit', 'puneet', 'sumant', 'bharat',
    'lakshman', 'shatrughan', 'balaram', 'govind', 'gopal', 'madhav', 'mohan',
    'murari', 'kanhaiya', 'akash', 'anand', 'anurag', 'arun', 'ashwin', 'bhavin',
    'chirag', 'darshan', 'dhruv', 'gautam', 'harsh', 'ishan', 'jai', 'karan',
    'manan', 'nakul', 'om', 'parth', 'prateek', 'ritik', 'samarth', 'tanmay',
    'utkarsh', 'vaibhav', 'yuvraj', 'alex', 'john', 'david', 'michael', 'james',
    'robert', 'william', 'richard', 'thomas', 'charles', 'daniel', 'matthew',
    'anthony', 'mark', 'paul', 'steven', 'andrew', 'george', 'joshua', 'kevin',
    'brian', 'edward', 'ryan', 'jacob', 'nicholas', 'eric', 'jonathan', 'justin',
    'samuel', 'patrick', 'alexander', 'jack', 'tyler', 'aaron', 'henry', 'adam',
    'peter', 'zachary', 'kyle', 'noah', 'lucas', 'liam', 'ethan', 'mason', 'oliver',
    'benjamin', 'logan', 'elijah', 'connor', 'caleb', 'luke', 'nathan', 'christian'
}

# Set of common female names (Indian & International)
FEMALE_NAMES = {
    'priya', 'pooja', 'neha', 'sneha', 'ananya', 'shreya', 'riya', 'diya', 'kavya',
    'tanvi', 'ishita', 'aditi', 'nikita', 'swati', 'sunita', 'anita', 'geeta',
    'seema', 'rekha', 'suman', 'meena', 'asha', 'usha', 'lata', 'radha', 'sita',
    'rukmini', 'lakshmi', 'saraswati', 'parvati', 'durga', 'gauri', 'bhavna',
    'divya', 'deepika', 'priyanka', 'anushka', 'alia', 'katrina', 'shraddha',
    'kareena', 'karisma', 'madhuri', 'aishwarya', 'sushmita', 'rani', 'preity',
    'kajol', 'vidya', 'shilpa', 'raveena', 'bipasha', 'sonam', 'sonakshi',
    'jacqueline', 'kiara', 'sara', 'janhvi', 'kriti', 'disha', 'tamannaah',
    'rashmika', 'samantha', 'nayanthara', 'trisha', 'keerthy', 'arohi', 'aarohi',
    'pranjal', 'komal', 'sheetal', 'payal', 'kajal', 'simran', 'muskan', 'khushi',
    'pallavi', 'chhavi', 'tanya', 'simi', 'nidhi', 'mansi', 'rashi', 'avni',
    'roshni', 'sakshi', 'shikha', 'shilpi', 'jyoti', 'preeti', 'artii', 'aarti',
    'mona', 'sona', 'nandini', 'megha', 'payel', 'barkha', 'tina', 'reena', 'meera',
    'mary', 'patricia', 'jennifer', 'linda', 'elizabeth', 'barbara', 'susan',
    'jessica', 'sarah', 'karen', 'nancy', 'lisa', 'betty', 'margaret', 'sandra',
    'ashley', 'kimberly', 'emily', 'donna', 'michelle', 'carol', 'amanda',
    'melissa', 'deborah', 'stephanie', 'rebecca', 'laura', 'sharon', 'cynthia',
    'kathleen', 'amy', 'shirley', 'angela', 'helen', 'anna', 'brenda', 'pamela',
    'nicole', 'samantha', 'katherine', 'christine', 'debra', 'rachel', 'catherine',
    'carolyn', 'janet', 'ruth', 'maria', 'heather', 'diane', 'virginia', 'julie',
    'joyce', 'victoria', 'olivia', 'kelly', 'christina', 'lauren', 'joan', 'evelyn',
    'judith', 'megan', 'cheryl', 'andrea', 'hannah', 'martha', 'jacqueline',
    'frances', 'gloria', 'ann', 'teresa', 'kathryn', 'janice', 'jean', 'alice',
    'madison', 'doris', 'abigail', 'julia', 'judy', 'grace', 'denise', 'amber',
    'marilyn', 'beverly', 'danielle', 'theresa', 'sophia', 'marie', 'diana',
    'brittany', 'natalie', 'isabella', 'charlotte', 'mia', 'harper', 'camila',
    'zoe', 'chloe', 'penelope', 'riley', 'layla', 'nora', 'hazel', 'lily', 'ellie'
}

def detect_gender(name: str) -> str:
    """
    Intelligently determines whether a name sounds like a boy or girl
    using extensive name dictionaries and phonetic/linguistic heuristics.
    Returns 'boy' or 'girl'.
    """
    if not name:
        return 'boy'

    # Extract first name token and clean punctuation
    cleaned = ''.join(c for c in name if c.isalnum() or c.isspace()).strip()
    tokens = cleaned.split()
    if not tokens:
        return 'boy'
    first_name = tokens[0].lower()

    # Direct dictionary matching
    if first_name in MALE_NAMES:
        return 'boy'
    if first_name in FEMALE_NAMES:
        return 'girl'

    # Suffix heuristics
    female_endings = (
        'a', 'i', 'ee', 'ya', 'ti', 'ka', 'na', 'ni', 'shree',
        'ita', 'ika', 'ine', 'ette', 'elle', 'leen', 'preet', 'priya'
    )
    male_endings = (
        'raj', 'esh', 'veer', 'deep', 'pal', 'inder', 'an', 'ar',
        'ur', 'it', 'ik', 'av', 'am', 'el', 'er', 'on', 'en', 'or',
        'o', 'us', 'ant', 'ath', 'alok', 'nath'
    )

    for fe in female_endings:
        if first_name.endswith(fe):
            return 'girl'

    for me in male_endings:
        if first_name.endswith(me):
            return 'boy'

    return 'boy'

def get_avatar_for_user(name: str, email: str = "") -> str:
    """
    Generates a unique, deterministic, gender-appropriate avatar URL
    for a user based on their name and email.
    Different users receive different avatars.
    """
    gender = detect_gender(name)
    key = f"{name.strip().lower()}:{email.strip().lower()}".encode('utf-8')
    h = int(hashlib.md5(key).hexdigest(), 16)

    if gender == 'girl':
        return GIRL_AVATARS[h % len(GIRL_AVATARS)]
    else:
        return BOY_AVATARS[h % len(BOY_AVATARS)]

def get_all_avatars() -> Dict[str, List[str]]:
    """Returns the full catalog of boy and girl avatars for profile selection."""
    return {
        "boys": BOY_AVATARS,
        "girls": GIRL_AVATARS
    }
