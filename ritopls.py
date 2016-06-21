#mehabahaha
#41938767

# do i:
#  do more overall dmg
#  get more objectives
#  get more kills
#  get more assists
#  get more gold
#  get more cs
#  die less
#  play better with or without friends
#  play longer games with or without friends
#  play better in specific roles
#  play better with specific champions


import requests, json, time, itertools, collections, ast, datetime

from pymongo import MongoClient, errors


client = MongoClient()
db = client['test']
matches_collection = db['rito_matches']
stats_collection = db['rito_stats']

def convert(data):
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, float):
    	return float("{0:.2f}".format(data))
    elif isinstance(data, collections.Mapping):
        return dict(map(convert, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert, data))
    else:
        return data

url = 'https://na.api.pvp.net/api/lol/na/'
static_url = 'https://global.api.pvp.net/api/lol/static-data/na/'

def rito_pls(endpoint, params='', query='?', static=False):
	get_url = url
	if static:
		get_url = static_url

	request = get_url + endpoint + str(params) + str(query) + 'api_key=ef31dc19-b206-4753-8029-acc73903d5f5'
	resp = requests.get(request)

	if int(resp.status_code) == 429:
		if 'Retry-After' in resp.headers:
			retry_time = int(resp.headers['Retry-After']) + 1
		else:
			print('ritopls')
			retry_time = 11
		print('retrying %d rate limited' % (retry_time))
		time.sleep(retry_time)
		resp = requests.get(request)
			
	return resp.json()

def get_champion(champion_id):
	return rito_pls('v1.2/champion/', champion_id, '?champData=all&', True)

def get_summoners(summoner_ids_or_names):
	if type(summoner_ids_or_names) == list:
		summoner_id_or_name = ''
		for x in summoner_ids_or_names:
			summoner_id_or_name = summoner_id_or_name + str(x) + ',' 
		return rito_pls('v1.4/summoner/by-name/', summoner_id_or_name)

	if type(summoner_id_or_name) == str:
		return rito_pls('v1.4/summoner/by-name/', summoner_id_or_name)
	if type(summoner_id_or_name) == int:
		return rito_pls('v1.4/summoner/', summoner_id_or_name)

def get_matchlist(summoner_id):
	return rito_pls('v2.2/matchlist/by-summoner/', summoner_id)

def get_match(match_id):
	return rito_pls('v2.2/match/', match_id)

def get_one_matchlist(summs, name):
	for summ in summs:
		if summ == name:
			matchlist = get_matchlist(summs[summ]['id'])
			if matchlist:
				return matchlist

def run():
	# do not do cache false and all true
	CACHE = True
	ALL = True
	primary_summ = 'slawcat'
	summs_to_compare = sorted(['mehabahaha','rockologist','slawcat'])
	desired_stats = ['killingSprees','neutralMinionsKilled','largestMultiKill','towerKills','kills','totalDamageDealtToChampions','wardsPlaced','wardsKilled','deaths','assists','goldEarned','totalDamageTaken','minionsKilled']
	
	summs_combos = list(itertools.combinations(summs_to_compare, r=2))
	summs_combos.append(tuple(summs_to_compare))
	if ALL:
		for summ in summs_to_compare:
			summs_combos.append((summ,))
	else:
		summs_combos.append((primary_summ,))

	summs={u'mehabahaha': {u'profileIconId': 688, u'summonerLevel': 30, u'revisionDate': 1464378381000, u'id': 41938767, u'name': u'mehabahaha'}, u'slawcat': {u'profileIconId': 682, u'summonerLevel': 30, u'revisionDate': 1464704976000, u'id': 41261356, u'name': u'slawcat'}, u'rockologist': {u'profileIconId': 786, u'summonerLevel': 30, u'revisionDate': 1464653929000, u'id': 44154717, u'name': u'rockologist'}}
	# summs = get_summoners(summs_to_compare)		

	matches = {}
	if CACHE:
		if ALL:
			for summ in summs_to_compare:
				with open(summ + '_matches.txt', 'r') as destination:
					matches.update(ast.literal_eval(destination.read()))
		else:
			with open(primary_summ + '_matches.txt', 'r') as destination:
				matches = ast.literal_eval(destination.read())
	else:
		matchlist = get_one_matchlist(summs, primary_summ)
		for m in matchlist['matches']:
			match = get_match(m['matchId'])
			if 'participantIdentities' in match:
				matches[match['matchId']] = match

	if ALL:
		primary_summ = 'ALL'
	with open(primary_summ + '_matches.txt', 'w') as destination:
		destination.write(str(matches))

	matches_to_players = {}
	for match in matches:

		matches_collection.update_one({'mid': match}, {'$set': {"mid": match, "i": matches[match]}}, upsert=True)

		match_people = matches[match]['participantIdentities']	
		match_usernames = []
		for person in match_people:
			if person['player']['summonerName'] in summs.keys():
				match_usernames.append((person['player']['summonerName'], person['participantId']))
		matches_to_players[match] = match_usernames

	averages = {}
	champs_played = {}
	total_games = {}
	for pair in summs_combos:
		averages[pair] = {}
		champs_played[pair] = {}
		total_games[pair] = {}
		total_games[pair]['total'] = 0.0
		total_games[pair]['durations'] = 0.0
		total_games[pair]['wins'] = 0.0
		for summ in summs:
			if summ in pair:
				champs_played[pair][summ] = {}
				averages[pair][summ] = {}
				for stat in desired_stats:
					averages[pair][summ][stat] = 0

	known_champs = {}
	processed = 0
	oldest_game_id = matches_to_players.keys()[0]
	for mid in matches:
		print('processing match %d' % processed)
		processed += 1
		names = []
		for player in matches_to_players[mid]:
			names.append(player[0])
		pair = tuple(sorted(names))
		total_games[pair]['total'] += 1
		total_games[pair]['durations'] += matches[mid]['matchDuration']
		date = datetime.datetime.fromtimestamp(matches[mid]['matchCreation'] / 1000.0)
		
		if date < datetime.datetime.fromtimestamp(matches[oldest_game_id]['matchCreation'] / 1000.0):
			oldest_game_id = mid

		checkwin = False
		for player in matches[mid]['participants']:
			pid = player['participantId']
			cid = player['championId']
			if cid not in known_champs:
				known_champs[cid] = champ = get_champion(cid)['name']
			else:
				champ = known_champs[cid]
			for playa in matches_to_players[mid]:
				if playa[1] == pid:
					if champ not in champs_played[pair][playa[0]]:
						champs_played[pair][playa[0]][champ] = 1
					else:
						champs_played[pair][playa[0]][champ] = champs_played[pair][playa[0]][champ] + 1

					for stat in desired_stats:
						averages[pair][playa[0]][stat] += player['stats'][stat]
					if player['stats']['winner'] and not checkwin:
						checkwin = True
						total_games[pair]['wins'] += 1

	for pair in averages:
		for summ in averages[pair]:
			for stat in averages[pair][summ]:
				averages[pair][summ][stat] = averages[pair][summ][stat] / (total_games[pair]['total'] or 1)

	for pair in total_games:
		total_games[pair]['durations'] = total_games[pair]['durations'] / (total_games[pair]['total'] or 1)
		total_games[pair]['winrate'] = total_games[pair]['wins'] / (total_games[pair]['total'] or 1)


	print('num games played and avg durations')
	print(convert(total_games))
	print('champions played')
	print(convert(champs_played))
	print('average stats:')
	print(convert(averages))
	# print('oldest game:')
	# print(matches[oldest_game_id])

# print(get_champion(99))
run()
