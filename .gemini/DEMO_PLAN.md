# Pragya System Demo Plan
## Technical Preparation & Execution Guide

**Meeting Date:** Thursday, February 13, 2026  
**Audience:** Managing Director + Senior Management  
**Demo Duration:** 15-20 minutes  
**Total Meeting Duration:** 45-60 minutes (including Q&A and discussion)

---

## 📅 **Timeline Overview**

### **Week Before (Feb 6-12)**
- **Day -7 to -5**: Prepare presentation materials
- **Day -4 to -2**: Test system thoroughly, fix any bugs
- **Day -1**: Final rehearsal and system check
- **Day 0**: Demo day!

---

## 🔧 **Technical Setup Checklist**

### **System Requirements**

**Hardware:**
- [ ] Laptop/desktop with minimum 8GB RAM
- [ ] Stable internet connection (for web app)
- [ ] External monitor or projector for presentation
- [ ] HDMI/display cable (test before meeting)
- [ ] Backup laptop (in case of hardware failure)

**Software:**
- [ ] PostgreSQL database running
- [ ] Ollama installed and running
- [ ] Python virtual environment activated
- [ ] Node.js and npm installed
- [ ] All dependencies up to date

**Services to Start:**
- [ ] PostgreSQL (port 5432)
- [ ] Ollama (port 11434)
- [ ] Flask backend (port 5000)
- [ ] Next.js frontend (port 3000)

---

## 🚀 **Pre-Demo Setup (Day Before)**

### **1. System Health Check**

**Run these commands to verify everything works:**

```bash
# Check PostgreSQL
psql -U arya -d testdb -c "SELECT COUNT(*) FROM chunks_identity;"
# Expected: Should return total chunk count (500+)

# Check Ollama
curl http://localhost:11434/api/tags
# Expected: Should list available models

# Check Flask backend
curl http://localhost:5000/api/health
# Expected: {"status": "healthy"}

# Check Next.js frontend
curl http://localhost:3000/api/health
# Expected: {"status": "ok"}
```

**If any check fails:**
- Restart the service
- Check logs for errors
- Fix issues before demo day

---

### **2. Test All Demo Queries**

**Run each query and verify results:**

| Query | Expected Result | Status |
|-------|----------------|--------|
| "What is the definition of a company?" | Section 2(20) definition | ⬜ |
| "What are the requirements for appointing an independent director?" | Section 149 details | ⬜ |
| "What does Section 149 say about director appointments?" | Section 149 content | ⬜ |
| "What is the quorum for a board meeting?" | Section 174 details | ⬜ |
| "What is the definition of memorandum?" | Section 2(56) definition | ⬜ |

**For each query:**
- [ ] Response time < 10 seconds
- [ ] Answer is accurate and well-formatted
- [ ] Citations are correct
- [ ] Source documents are displayed
- [ ] No errors in console

**If any query fails:**
- Debug the issue
- Check retrieval logs
- Verify database has correct data
- Test alternative queries

---

### **3. Prepare Backup Materials**

**In case of technical failure:**

- [ ] **Screenshots**: Capture results for all demo queries
- [ ] **Screen Recording**: Record a full demo run-through
- [ ] **Printed Handouts**: Print key slides and sample results
- [ ] **Backup Laptop**: Have a second machine ready with system running
- [ ] **Offline Slides**: PowerPoint/PDF version of pitch deck

**Store these in:**
- USB drive
- Cloud storage (Google Drive/OneDrive)
- Email to yourself

---

### **4. Optimize System Performance**

**Close unnecessary applications:**
- [ ] Close all browser tabs except demo
- [ ] Close Slack, Teams, email clients
- [ ] Close resource-heavy applications
- [ ] Disable notifications (Windows Focus Assist / macOS Do Not Disturb)

**Optimize browser:**
- [ ] Clear browser cache
- [ ] Disable extensions (except essential ones)
- [ ] Set zoom to 125% for better visibility
- [ ] Bookmark http://localhost:3000 for quick access

**System settings:**
- [ ] Disable auto-updates
- [ ] Disable screen saver
- [ ] Set power plan to "High Performance"
- [ ] Ensure laptop is fully charged (or plugged in)

---

## 🎬 **Demo Day Setup (Morning Of)**

### **2 Hours Before Meeting**

**Start all services:**

```bash
# Terminal 1: Start PostgreSQL (if not running as service)
# Check if running:
docker ps | grep postgres

# Terminal 2: Start Ollama (if not running as service)
ollama serve

# Terminal 3: Start Flask backend
cd C:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013
C:\Users\kalid\OneDrive\Documents\RAG\.venv\Scripts\python.exe app_faiss.py

# Terminal 4: Start Next.js frontend
cd C:\Users\kalid\OneDrive\Documents\RAG\app
npm run dev
```

**Verify all services:**
- [ ] Open http://localhost:3000 - should load homepage
- [ ] Run a test query - should return results
- [ ] Check browser console - no errors
- [ ] Check Flask logs - no errors

---

### **1 Hour Before Meeting**

**Final checks:**

- [ ] **Test display connection**: Connect to projector/external monitor
- [ ] **Test audio**: If presenting virtually, test microphone and speakers
- [ ] **Test screen sharing**: If virtual, test screen sharing in meeting tool
- [ ] **Position windows**: Arrange browser and script on different screens
- [ ] **Prepare notes**: Have demo script open on tablet/second screen
- [ ] **Water and essentials**: Have water, tissues, etc. nearby

**Run through demo once more:**
- [ ] Execute all demo queries
- [ ] Time yourself (should be 15-20 minutes)
- [ ] Practice transitions between queries
- [ ] Practice narration

---

### **30 Minutes Before Meeting**

**Final preparations:**

- [ ] **Bathroom break** 🚻
- [ ] **Deep breaths** - calm nerves
- [ ] **Review key messages** from demo script
- [ ] **Check appearance** (if in-person or video)
- [ ] **Silence phone** 📵
- [ ] **Close all unnecessary apps**
- [ ] **Have backup materials ready**

**Set up presentation space:**
- [ ] Clean desk/background (if video)
- [ ] Good lighting (if video)
- [ ] Camera at eye level (if video)
- [ ] Comfortable seating
- [ ] Pen and paper for notes

---

## 🎯 **Demo Execution Plan**

### **Meeting Structure (60 minutes total)**

| Time | Activity | Duration |
|------|----------|----------|
| 0:00-0:05 | Welcome & Introduction | 5 min |
| 0:05-0:10 | Problem Statement (Slides) | 5 min |
| 0:10-0:30 | **LIVE DEMO** | 20 min |
| 0:30-0:40 | Solution Overview (Slides) | 10 min |
| 0:40-0:55 | Q&A | 15 min |
| 0:55-1:00 | Next Steps & Closing | 5 min |

---

### **Demo Sequence (20 minutes)**

**Follow this exact sequence:**

1. **[2 min]** Introduction to interface
   - Show homepage
   - Explain search bar
   - Point out example queries

2. **[3 min]** Demo Query 1: Definition
   - Query: "What is the definition of a company?"
   - Narrate while processing
   - Highlight answer, citation, sources

3. **[4 min]** Demo Query 2: Procedural
   - Query: "What are the requirements for appointing an independent director?"
   - Show structured answer
   - Highlight multiple citations

4. **[3 min]** Demo Query 3: Section-specific
   - Query: "What does Section 149 say about director appointments?"
   - Show cross-reference resolution

5. **[4 min]** Demo Query 4: Business scenario
   - Query: "What is the quorum for a board meeting?"
   - Emphasize real-world applicability

6. **[2 min]** Mobile responsiveness
   - Resize browser to mobile view
   - Show it works on any device

7. **[2 min]** Highlight key features
   - Speed, accuracy, citations, ease of use

---

## 📊 **Monitoring During Demo**

### **What to Watch For**

**Good signs:**
- ✅ MD is nodding
- ✅ MD is taking notes
- ✅ MD asks questions (shows engagement)
- ✅ MD leans forward (shows interest)
- ✅ MD smiles or shows positive reactions

**Warning signs:**
- ⚠️ MD looks confused (slow down, clarify)
- ⚠️ MD is distracted (re-engage with question)
- ⚠️ MD looks skeptical (address concerns proactively)
- ⚠️ MD checks watch (speed up, get to the point)

**Adjust accordingly:**
- If engaged: Take time, show more examples
- If rushed: Skip to key demos, summarize quickly
- If skeptical: Focus on accuracy and citations
- If excited: Discuss next steps and deployment

---

## 🚨 **Troubleshooting Guide**

### **Issue: System is slow**

**Symptoms:** Queries taking >15 seconds

**Quick fixes:**
1. Check if Ollama is running: `curl http://localhost:11434/api/tags`
2. Restart Flask backend
3. Clear browser cache and reload
4. If persists, use backup screenshots

---

### **Issue: Wrong answer appears**

**Symptoms:** Answer doesn't match expected result

**Quick fixes:**
1. Acknowledge: "Interesting, let me try a different query"
2. Move to next demo query
3. Explain: "This shows we're continuously improving the system"
4. Don't dwell on it - move forward confidently

---

### **Issue: Service crashes**

**Symptoms:** Error page, connection refused

**Quick fixes:**
1. **Stay calm** - don't panic
2. Say: "Let me quickly restart the service"
3. Restart Flask backend in terminal
4. Refresh browser
5. If doesn't work in 30 seconds, switch to backup materials

---

### **Issue: Display/projector problems**

**Symptoms:** Screen not showing, resolution issues

**Quick fixes:**
1. Have backup laptop ready
2. Use Windows+P to switch display modes
3. Adjust resolution if needed
4. Worst case: Show on laptop screen, gather around

---

## 📝 **Post-Demo Actions**

### **Immediately After Meeting**

**Within 1 hour:**
- [ ] Send thank-you email to MD
- [ ] Attach pitch deck PDF
- [ ] Summarize key discussion points
- [ ] Note any commitments made
- [ ] Share demo recording (if recorded)

**Email template:**

```
Subject: Thank You - Pragya Demo & Next Steps

Dear [MD Name],

Thank you for taking the time to see the Pragya demonstration today. 

As discussed, Pragya can provide instant, accurate answers to Companies Act queries, 
saving significant time and reducing compliance risk.

Attached:
- Pitch deck (PDF)
- Demo recording (if available)
- Technical documentation

Next Steps (as discussed):
- [List agreed-upon next steps]

I'm available to answer any follow-up questions or provide additional information.

Best regards,
[Your Name]
```

---

### **Within 24 Hours**

- [ ] **Debrief with team**: What went well, what to improve
- [ ] **Document feedback**: Note all questions and concerns raised
- [ ] **Update materials**: Improve pitch deck based on feedback
- [ ] **Prepare follow-up**: If pilot approved, prepare deployment plan

---

### **Within 1 Week**

- [ ] **Follow up on decision**: Politely check status
- [ ] **Address outstanding questions**: Provide detailed answers
- [ ] **Prepare next phase**: Pilot plan, training materials, etc.

---

## ✅ **Success Criteria**

**The demo is successful if:**

- [ ] MD understands what Pragya does
- [ ] MD sees the business value (time/cost savings)
- [ ] MD is convinced of accuracy and reliability
- [ ] MD approves pilot deployment OR requests more information
- [ ] MD allocates budget OR commits to next steps
- [ ] MD asks to show other stakeholders (CFO, Legal, etc.)

**Bonus success:**
- [ ] MD tries it themselves during demo
- [ ] MD shares specific use cases from their experience
- [ ] MD asks about expansion to other laws
- [ ] MD mentions it in next leadership meeting

---

## 🎯 **Key Metrics to Track**

### **During Demo**

- [ ] Number of queries demonstrated: Target 4-5
- [ ] Average response time: Target <5 seconds
- [ ] Number of questions from MD: More = better engagement
- [ ] Time spent on demo: Target 15-20 minutes
- [ ] Positive reactions: Nods, smiles, "wow" moments

### **After Demo**

- [ ] Decision timeline: When will MD decide?
- [ ] Budget approval: Amount and timeline
- [ ] Pilot scope: How many users, which departments?
- [ ] Next meeting: When to follow up?
- [ ] Stakeholder expansion: Who else to show?

---

## 💡 **Pro Tips**

### **Before Demo**
1. **Practice, practice, practice** - run through 3-5 times
2. **Time yourself** - ensure you stay within 20 minutes
3. **Prepare for questions** - review Q&A section
4. **Get good sleep** - be fresh and alert
5. **Arrive early** - set up without rushing

### **During Demo**
1. **Speak slowly** - MD may not be tech-savvy
2. **Pause for effect** - let results sink in
3. **Make eye contact** - don't just stare at screen
4. **Show enthusiasm** - your energy is contagious
5. **Be honest** - admit limitations, don't oversell

### **After Demo**
1. **Thank everyone** - show appreciation
2. **Follow up promptly** - strike while iron is hot
3. **Be patient** - decisions take time
4. **Stay positive** - even if not immediate approval
5. **Keep improving** - use feedback to enhance system

---

## 📎 **Resource Checklist**

### **Digital Resources**

- [ ] Pitch deck (Markdown/PDF/PowerPoint)
- [ ] Demo script (this document)
- [ ] Technical documentation
- [ ] Screenshots of demo results
- [ ] Screen recording of demo
- [ ] Cost/ROI analysis spreadsheet
- [ ] Pilot deployment plan

### **Physical Resources**

- [ ] Laptop (fully charged)
- [ ] Backup laptop
- [ ] HDMI cable
- [ ] USB drive with backups
- [ ] Printed pitch deck
- [ ] Printed demo script
- [ ] Business cards
- [ ] Pen and notepad
- [ ] Water bottle

### **Access & Credentials**

- [ ] Database credentials
- [ ] Server access (if remote)
- [ ] Meeting room booking
- [ ] Video conferencing link (if virtual)
- [ ] Screen sharing permissions
- [ ] Admin access to demo system

---

## 🎓 **Lessons Learned Template**

**After the demo, fill this out:**

### **What Went Well**
- 
- 
- 

### **What Could Be Improved**
- 
- 
- 

### **Unexpected Questions**
- 
- 
- 

### **Technical Issues**
- 
- 
- 

### **Action Items for Next Time**
- 
- 
- 

---

## 🚀 **Next Steps After Approval**

### **If MD Approves Pilot**

**Week 1:**
- [ ] Identify 10-15 pilot users
- [ ] Set up production environment
- [ ] Configure user authentication
- [ ] Prepare training materials

**Week 2:**
- [ ] Conduct training sessions
- [ ] Deploy to pilot users
- [ ] Set up monitoring and feedback collection
- [ ] Daily check-ins with users

**Week 3-4:**
- [ ] Gather feedback
- [ ] Fix issues
- [ ] Measure usage metrics
- [ ] Prepare pilot report

**Month 2:**
- [ ] Present pilot results to MD
- [ ] Get approval for full rollout
- [ ] Plan organization-wide deployment

---

## 📞 **Emergency Contacts**

**Have these ready during demo:**

- **IT Support**: [Phone/Email]
- **Database Admin**: [Phone/Email]
- **Backup Presenter**: [Phone/Email]
- **Meeting Organizer**: [Phone/Email]

---

## 🎯 **Final Checklist - Morning Of Demo**

**Print this and check off:**

- [ ] All services running (PostgreSQL, Ollama, Flask, Next.js)
- [ ] Test query executed successfully
- [ ] Display/projector connected and working
- [ ] Backup materials ready (screenshots, recording, printed slides)
- [ ] Demo script open and accessible
- [ ] Notifications disabled
- [ ] Phone silenced
- [ ] Water and essentials ready
- [ ] Comfortable and confident
- [ ] Ready to impress! 🚀

---

**Good luck! You've prepared thoroughly. Trust your preparation and deliver with confidence!**

---

**END OF DEMO PLAN**
