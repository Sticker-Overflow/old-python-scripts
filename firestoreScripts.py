from google.cloud import firestore
import sys, os, uuid
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from dateutil.parser import parse

# This script has only been tested on Ubuntu

# This assumes one has the gcloud client on their machine with the stickeroverflow project set as the default google project
db = firestore.Client()
orgsCollectionReference = db.collection(u'organizations')
hackathonsCollectionReference = db.collection(u'hackathons')

# Go through each hackathon's page and add these by hand
def putSponsorsIntoFirestore():
	sponsors = ["Hello World", "Giphy", "Docker", "NASA", "Google", "Microsoft", "Facebook", "Securable.io", "wit.ai", "GitHub", "Amazon",
	"Best Buy",	"PagerDuty", "Linode", "FitBit", "A Thinking Ape", "Flipp", "Sun Life Financial", "Junction", "Mashape", "Devpost", "Firebase", "Namecheap", "Twilio", 
	"Salesforce", "Lyft", "Uber", "GE", "Capital One", "DRW", "Atomic Object", "Walmart", "Emotive", "Wolfram Alpha", "HTC", "CVS", "a16z", "Goldman Sachs",
	"Square Space", "Vonage", "Airbnb", "Soylent", "Bloomberg", "Oracle", "Qualtrics", "Deloitte Digital", "RBC", "Velocity", "Shopify", "Cockroach DB", "Coinbase", "IBM", 
	"Manifold", "Magnet Forensics", "Arcelor Mittal", "State Farm", "Rockwell Collins", "Mixmax", "Sticker Mule", "Muse", "StickerYou.com", ".tech Domains",
	"Sparkfun Electronics", "Starbucks", "Dell", "Intel", "Nest", "GitLab", "Chevron", "Indeed", "Exxon Mobil", "Spotify", "Cisco", "FirstBuild", "Akamai", "RedHat", "3M",
	"VM Ware", "Pendo", "Adobe", "Digital Ocean", "Sketch", "Launch Academy", "Spring", "Picatic", "Lighthouse Labs", "Vidia", "Dataspeed Inc.", "Intrepid CS", "RIIS",
	"Quicken Loans", "Allstate", "Progressive", "Hyland", "Nationwide", "DeepHire", "UltraPress", "Boogie Board", "Drund", "PowerDMS", "Sonobi", "Ebay"
	"Liberty Mutual Insurance", "Shopbop", "Citi", "Epic", "Widen", "Singlewire Software", "PerBlue", "Black Rock", "Honeywell", "Dice", "EFX", "Siemens", "Macy's", "Delta",
	"Deepscale", "General Motors", "AT&T", "Cerner", "Pivotal", "Tradebot", "Voatz", "3Red", "Guidebook", "Wells Fargo", "Leidos", "Qualcomm", "Webroot", "Northrop Grumman",
	"Nanome", "Awakens", "Jumpstart", "Chick-fil-A", "Fly.io", "The Home Depot", "Disney", "Expedia", "CIA", "NSA", "SAP", "Zillow", "Discover", "Motorola", "balsamiq", "Pepsi"]

	for s in sponsors:
		# Finish adding data at a later date
		sponsor = {
			"id": str(uuid.uuid4()),
			"name": s,
			"description": "TODO",
			"location": "TODO",
			"logoURL": "TODO",
			"url": "TODO"
		}
		db.collection("sponsors").document(sponsor['id']).set(sponsor)

# Add organizers by hand 
def putOrganizersIntoFirebase():
	organizers = ["MHacks", "Grizz Hacks", "Sparta Hack", "Hack The North", "PennApps", "MedHacks", "HopHacks", "RamHacks", "HackRice", "BoilerMake", "ShellHacks", "EduHacks",
	"Kent Hack Enough", "MadHacks", "HackHarvard", "HackISU", "HackNC", "HackPSU", "Hack AE", "HackPrinceton", "WHACK", "Hakital", "Hack Western", "YHack", "DragonHacks", "MLH"]

	for o in organizers:
		organizer = {
			"id": str(uuid.uuid4()),
			"name": o,
			"description": "TODO",
			"location": "TODO",
			"logoURL": "TODO",
			"url": "TODO"
		}

		db.collection("organizers").document(organizer['id']).set(organizer)

# Anything we pull with BS4 that contains an @ is considered by CloudFlare to be an email so to decode it we have to use this
def decodeEmail(e):
	de = ""
	k = int(e[:2], 16)
	for i in range(2, len(e) - 1, 2):
		de += chr(int(e[i:i+2], 16)^k)
	return de

# This should become obsolete once MLH releases their API (Mike mentioned it would happen a couple weeks after Hackcon)
def putHackathonsIntoFirestore():
	urls = [
		"https://mlh.io/seasons/na-2019/events",
		"https://mlh.io/seasons/eu-2019/events",
		"http://mlh.io/seasons/na-2018/events", 
		"http://mlh.io/seasons/eu-2018/events",
		"http://mlh.io/seasons/na-2017/events", 
		"http://mlh.io/seasons/eu-2017/events",
		"http://mlh.io/seasons/s2016/events",
		"http://mlh.io/seasons/s2015/events",
		"http://mlh.io/seasons/s2014/events",
		"http://mlh.io/seasons/f2013/events",
		"http://mlh.io/seasons/f2014/events",
		"http://mlh.io/seasons/f2015/events"
	]

	years = ["2018", "2017", "2016", "2015", "2014", "2013"]
	# Only needed for the most recent years since mlh has their seasons listed a year ahead (not really but kinda)
	yearsDict = {"2018": 2018, "2017": 2017}
	earlyMonths = ["Aug", "Sep", "Oct", "Nov", "Dec"]
	newYears = ["2018", "2017"]

	for url in urls:
		req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
		page = urlopen(req).read()
		soup = BeautifulSoup(page, 'html.parser')
		hackathonNames = soup.findAll("h3", attrs={'itemprop': 'name'})
		for hackathonName in hackathonNames:
			for year in years:
				if year in url.split("seasons/")[1].split("/events")[0]:
					if hackathonName.parent.parent.findNext("p").contents[0].split(" ")[0] in earlyMonths and year in newYears:
						hackathonYear = str(yearsDict[year] - 1)
					else:
						hackathonYear = year
					break
				else:
					hackathonYear = "N/A"
					
			hackathon = {}
			hackathon["location"] = hackathonName.parent.parent.findNext("span").contents[0] + ", " + hackathonName.parent.parent.findNext("span").findNext("span").contents[0]
			if "protected" in hackathonName.string and "email" in hackathonName.string:
				hackathon["name"] = decodeEmail(hackathonName.find("span")['data-cfemail'])
			else:
				hackathon["name"] = hackathonName.text
			hackathon["dateString"] = hackathonName.parent.parent.findNext("p").contents[0] + ", " + hackathonYear
			if "-" in hackathon["dateString"]:
				hDate = parse(hackathon["dateString"].split("-")[0] + hackathon["dateString"].split("-")[1].split(",")[1])
			else:
				hDate = parse(hackathon["dateString"])
			
			hackathon["date"] = hDate
			hackathon["url"] = hackathonName.findPrevious("a", href=True)["href"]
			hackathon["id"] = str(uuid.uuid4())
			hackathon["logoURL"] = hackathonName.findPrevious("img")["src"]
			hackathon["splashURL"] = hackathonName.findPrevious("img").findPrevious("img")["src"]
			hackathonsCollectionReference.document(hackathon["id"]).set(hackathon)

if __name__ == '__main__':
	# Running these more than once will result in duplicate data in Firestore. If a mistake is found and the scripts need to be re-run, delete the data from Firestore first
	putHackathonsIntoFirestore()
	putSponsorsIntoFirestore()
	putOrganizersIntoFirebase()