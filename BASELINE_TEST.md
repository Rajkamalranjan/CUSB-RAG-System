# CUSB RAG Baseline Evaluation - Test Protocol

**Date:** 2026-05-01  
**Tester:** Manual Evaluation  
**System:** CUSB AI Chatbot v2.0

---

## Test Instructions

1. Start chatbot: `python src/3_chatbot.py`
2. For each query below, test in chatbot
3. Record the answer and time
4. Check if expected keywords are present
5. Mark as PASS (✅) or FAIL (❌)

---

## Test Cases

### 1. General Knowledge
**Query:** CUSB kya hai?  
**Expected Keywords:** central university, gaya, bihar, 2009  
**Category:** general  
**Language:** hindi

**Chatbot Answer:**
```
[PASTE ANSWER HERE]
```

**Response Time:** ___ seconds  
**Keywords Found:** ___/4  
**Status:** ___ (PASS/FAIL)

---

### 2. Fee Query - M.Sc
**Query:** M.Sc Statistics ki fees kitni hai?  
**Expected Keywords:** 26,072, statistics, fees  
**Category:** fees  
**Language:** hinglish

**Chatbot Answer:**
```
[PASTE ANSWER HERE]
```

**Response Time:** ___ seconds  
**Keywords Found:** ___/3  
**Status:** ___ (PASS/FAIL)

---

### 3. Hostel Fees
**Query:** Hostel fee kitni hai?  
**Expected Keywords:** 9,000, hostel, mess, 3000  
**Category:** fees  
**Language:** hindi

**Chatbot Answer:**
```
[PASTE ANSWER HERE]
```

**Response Time:** ___ seconds  
**Keywords Found:** ___/4  
**Status:** ___ (PASS/FAIL)

---

### 4. Faculty Query
**Query:** Statistics department ke faculty kaun hain?  
**Expected Keywords:** professor, faculty, sunit, statistics  
**Category:** faculty  
**Language:** hinglish

**Chatbot Answer:**
```
[PASTE ANSWER HERE]
```

**Response Time:** ___ seconds  
**Keywords Found:** ___/4  
**Status:** ___ (PASS/FAIL)

---

### 5. Admission Process
**Query:** Admission process kya hai?  
**Expected Keywords:** cuet, entrance, exam, online, application  
**Category:** admission  
**Language:** hindi

**Chatbot Answer:**
```
[PASTE ANSWER HERE]
```

**Response Time:** ___ seconds  
**Keywords Found:** ___/5  
**Status:** ___ (PASS/FAIL)

---

### 6. NAAC Grade
**Query:** CUSB ka NAAC grade kya hai?  
**Expected Keywords:** naac, a++, grade, a plus  
**Category:** general  
**Language:** hindi

**Chatbot Answer:**
```
[PASTE ANSWER HERE]
```

**Response Time:** ___ seconds  
**Keywords Found:** ___/4  
**Status:** ___ (PASS/FAIL)

---

### 7. Course Count
**Query:** M.Sc kitne courses hain CUSB mein?  
**Expected Keywords:** 25, mathematics, statistics, computer, biotechnology  
**Category:** courses  
**Language:** hinglish

**Chatbot Answer:**
```
[PASTE ANSWER HERE]
```

**Response Time:** ___ seconds  
**Keywords Found:** ___/5  
**Status:** ___ (PASS/FAIL)

---

### 8. HOD Query
**Query:** Environmental Sciences ke HOD kaun hai?  
**Expected Keywords:** hod, head, environmental, dr, pradeep  
**Category:** faculty  
**Language:** hindi

**Chatbot Answer:**
```
[PASTE ANSWER HERE]
```

**Response Time:** ___ seconds  
**Keywords Found:** ___/5  
**Status:** ___ (PASS/FAIL)

---

### 9. CUET Information
**Query:** CUET kya hai?  
**Expected Keywords:** cuet, entrance, exam, common, university  
**Category:** admission  
**Language:** hindi

**Chatbot Answer:**
```
[PASTE ANSWER HERE]
```

**Response Time:** ___ seconds  
**Keywords Found:** ___/5  
**Status:** ___ (PASS/FAIL)

---

### 10. PhD Fees
**Query:** PhD ki fees kitni hai?  
**Expected Keywords:** phd, 7,600, 7600, 5,000, semester  
**Category:** fees  
**Language:** hindi

**Chatbot Answer:**
```
[PASTE ANSWER HERE]
```

**Response Time:** ___ seconds  
**Keywords Found:** ___/5  
**Status:** ___ (PASS/FAIL)

---

## Summary

### Overall Metrics

| Metric | Value |
|--------|-------|
| **Total Tests** | 10 |
| **Passed** | ___ |
| **Failed** | ___ |
| **Success Rate** | ___% |
| **Avg Response Time** | ___s |
| **Avg Keyword Score** | ___% |

### Category Breakdown

| Category | Tests | Passed | Success Rate |
|----------|-------|--------|--------------|
| General | 2 | ___ | ___% |
| Fees | 3 | ___ | ___% |
| Faculty | 2 | ___ | ___% |
| Admission | 2 | ___ | ___% |
| Courses | 1 | ___ | ___% |

### Language Breakdown

| Language | Tests | Passed | Success Rate |
|----------|-------|--------|--------------|
| Hindi | 6 | ___ | ___% |
| Hinglish | 4 | ___ | ___% |

---

## Observations

### Strengths
1. 
2. 
3. 

### Weaknesses
1. 
2. 
3. 

### Suggested Improvements
1. 
2. 
3. 

---

## Conclusion

**Overall Status:** ___ (EXCELLENT/GOOD/NEEDS_IMPROVEMENT/POOR)

**Recommendation:**
- If success rate >= 80%: System is production-ready
- If success rate 60-79%: Minor improvements needed
- If success rate < 60%: Major improvements required

**Next Steps:**
1. 
2. 
3. 

---

**Evaluator Signature:** _______________  
**Date:** _______________
