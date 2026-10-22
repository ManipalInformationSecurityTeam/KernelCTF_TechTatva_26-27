# Oath Declared

## Jane-7710

## Webex 

## Medium

## Question Description
Under Department Protocol 73, all formal declarations must be submitted in .docx format. The department's ingestion system performs a long sequence of compliance and injection checks before granting clearance.
The process is intentionally tedious, and some information submitted during one stage may be relevant again during a later stage. Certain steps may also be more dependent on order than they initially appear.

## Files needed
1. basic hosted website
   
## Intended Solution
1. Players upload a .docx to a website that checks a large number of annoying requirements involving specific text, formatting, metadata, document structure, etc.
2. Only one requirement is shown at a time. If it fails, the same requirement is shown again; only a successful check reveals the next one. The question order is randomized, with a few deliberately placed breadcrumb requirements.
3. The honest route is to continue satisfying the requirements until the declaration receives final editorial clearance.
4. The application contains a second-order template-rendering flaw: text from the submitted DOCX is processed again during a later audit-rendering stage.
5. Players can discover this by testing a template expression such as {{7*7}} in the declaration body and observing the evaluated result in the generated audit output. Multiple hints towards this appear before question 15 itself
6. The system logs directly give them the intended path document->audit->review->complete editorial review.
7. Calling that method through the second-order SSTI directly returns the flag.
Intended Exploit
{{ document.audit.review.complete_editorial_review() }}
8. The website then returns them the flag

### Flag

> kernel{ph3w_d3d1c4t10n_1s_t3d10us}
