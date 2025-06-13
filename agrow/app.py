from flask  import Flask, render_template, request, redirect, session, url_for, jsonify, flash
from pymongo import MongoClient
import uuid
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import pandas as pd
import json
from bson import ObjectId, json_util
import bcrypt
import os
import logging

app = Flask(__name__)


app.config['MONGO_URI'] = 'mongodb://localhost:27017/agrow'
client = MongoClient(app.config['MONGO_URI'])
db = client.get_database()
users_collection = db['akun']
berita_collection = db['konten_berita']
infoH_collection = db['info_Hpasar']
penawaran_collection = db['penjualan']
provinsi_collection = db['provinsi']
kabupaten_collection = db['kabupaten']
kecamatan_collection = db['kecamatan']
desa_collection = db['desa']
catatan_collection = db['catatan']

app.config['UPLOAD_FOLDER'] = os.path.realpath('.') + '/program/agrow/static/img'
def get_harga_pasar_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    query = {
        "waktu": {"$gte": start_date, "$lte": end_date}
    }
    data = list(infoH_collection.find(query))
    df = pd.DataFrame(data)

    if df.empty:
        return None

    df = df.sort_values(by="waktu", ascending=False).groupby(['comodity', 'province']).head(5)
    top_provinces = df.groupby('comodity')['province'].apply(lambda x: x.value_counts().index[:5])
    charts = {commodity: [] for commodity in df["comodity"].unique()}
    for commodity in df["comodity"].unique():
        provinces = top_provinces.get(commodity, [])
        for province in provinces:
            df_filtered = df[(df["comodity"] == commodity) & (df["province"] == province)]
            if not df_filtered.empty:
                df_filtered = df_filtered.sort_values(by="waktu") 
                chart_data = df_filtered.to_dict('records')
                charts[commodity].append({
                    "province": province,
                    "data": chart_data
                })
    return charts 

def get_berita_data():
    berita = list(berita_collection.find({}).limit(5)) 
    return berita
    
@app.route('/')
def beranda():
    return render_template('beranda.html')

@app.route('/home')
def home():
    current_date = datetime.now().strftime('%Y-%m-%d')  # Mendapatkan tanggal terbaru
    harga_pasar_data = get_harga_pasar_data()
    berita_data = get_berita_data()
    user = users_collection.find_one({'phone': session.get('phone')})
    role = session.get('role')
    return render_template('home.html', current_date=current_date, harga_pasar_data=harga_pasar_data, berita_data=berita_data, user=user, role=role)


def get_harga_pasar_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    query = {
        "waktu": {"$gte": start_date, "$lte": end_date}
    }
    data = list(infoH_collection.find(query))
    df = pd.DataFrame(data)

    if df.empty:
        return {}
    
    df = df.sort_values(by="waktu", ascending=False).groupby(['comodity', 'province']).head(5)
    top_provinces = df.groupby('comodity')['province'].apply(lambda x: x.value_counts().index[:5])
    charts = {commodity: [] for commodity in df["comodity"].unique()}
    for commodity in df["comodity"].unique():
        provinces = top_provinces.get(commodity, [])
        for province in provinces:
            df_filtered = df[(df["comodity"] == commodity) & (df["province"] == province)]
            if not df_filtered.empty:
                df_filtered = df_filtered.sort_values(by="waktu")
                chart_data = df_filtered.to_dict('records')
                for record in chart_data:
                    record['_id'] = str(record['_id']) 
                charts[commodity].append({
                    "comodity": commodity,
                    "province": province,
                    "data": chart_data
                })
    return charts

def get_berita_data():
    berita = list(berita_collection.find({}).limit(5))
    for item in berita:
        item['_id'] = str(item['_id']) 
    return berita


@app.route('/data', methods=['GET'])
def get_data():
    try:
        harga_pasar_data = get_harga_pasar_data()
        berita_data = get_berita_data()
        combined_data = {
            "harga_pasar_data": harga_pasar_data,
            "berita_data": berita_data
        }
        if not harga_pasar_data or not berita_data:
            return jsonify({"error": "No data found"}), 404
        return jsonify(json.loads(json_util.dumps(combined_data)))
    except Exception as e:
        logging.error(f"Error generating data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/harga_pasar_data', methods=['GET'])
def harga_pasar():
    user = users_collection.find_one({'phone': session.get('phone')})
    try:
        harga_pasar_data = get_harga_pasar_data()
        if not harga_pasar_data:
            return jsonify({"error": "No data found"}), 404
        return jsonify(json.loads(json_util.dumps(harga_pasar_data)))
    except Exception as e:
        logging.error(f"Error fetching harga pasar data: {e}")
        return jsonify({"error": "Internal server error"}), 500
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form['role']
        name = request.form['name']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        commodities = request.form.get('commodities') if role == 'distributor' else None

        if not name or not phone or not password or not confirm_password:
            flash('Semua kolom harus diisi!', 'danger')
        elif password != confirm_password:
            flash('Konfirmasi password tidak cocok!', 'danger')
        else:
            existing_user = users_collection.find_one({'phone': phone})
            if existing_user is None:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                new_user = {
                    'name': name,
                    'phone': phone,
                    'password': hashed_password,
                    'role': role,
                    "province": "",
                    "city": "",
                    "subdistrict": "",
                    "village": "",
                    "address": "",
                    "image": "",
                }
                if role == 'distributor':
                    new_user['comoditiy'] = ''
                users_collection.insert_one(new_user)
                session['username'] = name
                flash(f'Registrasi berhasil sebagai {role}!', 'success')
                return redirect(url_for('login'))
            flash('Nomor telepon sudah terdaftar!', 'danger')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        phone = request.form['phone']
        password = request.form['password']

        if not phone or not password or not role:
            flash('Semua kolom harus diisi!', 'danger')
        else:
            user = users_collection.find_one({'phone': phone, 'role': role})
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
                session['username'] = user['name']
                session['phone'] = user['phone']
                session['role'] = user['role']
                session['desa'] = user['village']
                flash('Login berhasil!', 'success')
                if 'phone' in session:
                    return redirect(url_for('home', user=user))
            flash('Nomor telepon, password, atau role salah!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout!', 'info')
    return render_template('beranda.html')

@app.route('/profile')
def profile():
    
    user = users_collection.find_one({'phone': session.get('phone')})
    provinsi = list(provinsi_collection.find({}))
    
    if user:
        user['_id'] = str(user['_id'])
        user.setdefault('image', 'default.png')
    else:
        user = {
            'name': session.get('username'),
            'phone': '',
            'province': '',
            'kabupaten': '',
            'kecamatan': '',
            'address': '',
            'image': 'default.png',
            'comodity': ''
        }
    
    return render_template('profile.html', user=user, provinsi=provinsi)

@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session.get('phone')
    user = users_collection.find_one({'phone': username})
    
    if 'image' in request.files:
        image = request.files['image']
        if image.filename != '':
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            user['image'] = filename

    province_id = request.form['province']
    kabupaten_id = request.form['kabupaten']
    kecamatan_id = request.form['kecamatan']
    desa_id = request.form['desa']

    province = provinsi_collection.find_one({'id': province_id})
    kabupaten = kabupaten_collection.find_one({'id': kabupaten_id})
    kecamatan = kecamatan_collection.find_one({'id': kecamatan_id})
    desa = desa_collection.find_one({'id': desa_id})

    user['name'] = request.form['name']
    user['phone'] = request.form['phone']
    user['province'] = province['name'] if province else ''
    user['city'] = kabupaten['name'] if kabupaten else ''
    user['subdistrict'] = kecamatan['name'] if kecamatan else ''
    user['village'] = desa['name'] if desa else ''
    user['address'] = request.form['address']

    if session.get('role') == 'distributor':
        user['comodity'] = request.form['comodity']

    users_collection.update_one({'phone': username}, {'$set': user})
    flash('Profil berhasil diperbarui', 'success')
    return redirect(url_for('profile'))

@app.route('/jual', methods=['GET'])
def jual():
    user = users_collection.find_one({'phone': session.get('phone')})
    step = request.args.get('step', '1')
    offers = penawaran_collection.find({'petani': session.get('username'), 'status': {'$ne': 'telah diambil'}})
    offers_list = []
    for offer in offers:
        offer['_id'] = str(offer['_id'])
        offers_list.append(offer)
    
    commodity = session.get('commodity', '')
    quantity = session.get('quantity', '')
    price = session.get('price', '')
    har = session.get('har')

    if commodity:
        distributors = list(users_collection.find({'role': 'distributor', 'commodity': commodity}))
    else:
        distributors = list(users_collection.find({'role': 'distributor'}))

    for distributor in distributors:
        distributor['_id'] = str(distributor['_id'])

    show_offers = len(offers_list) > 0

    return render_template('jual.html', offers=offers_list, distributors=distributors, show_offers=show_offers, step=step, user=user, commodity=commodity, quantity=quantity, price=price, har=har)


@app.route('/offer', methods=['POST'])
def offer():
    user = users_collection.find_one({'phone': session.get('phone')})
    step = request.form['step']
    if step == '1':
        session['commodity'] = request.form['commodity']
        return redirect(url_for('jual', step=2))

    elif step == '2':
        session.get('commodity')
        session['quantity'] = request.form['quantity']
        harga = infoH_collection.find_one({'comodity': session.get('commodity'), 'province': user['province']})
        har = harga['price'] * float(session.get('quantity'))
        session['har'] = har
        return redirect(url_for('jual', step=3))

    elif step == '3':
        session.get('commodity')
        har=session.get('har')
        session['price'] = request.form['price']
        return redirect(url_for('jual', step=4))

    elif step == '4':
        session.get('commodity')
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('jual', step=4))
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(url_for('jual', step=4))
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(filepath)
                session['file'] = filename
                return redirect(url_for('jual', step=5))
            except Exception as e:
                flash(str(e), 'danger')
                return redirect(url_for('jual', step=4))

    elif step == '5':
        session['distributor'] = request.form.getlist('distributor')
        save_offer()
        return redirect(url_for('jual'))

@app.route('/update_offer', methods=['POST'])
def update_offer():
    offer_id = request.form['offer_id']
    action = request.form['action']
    offer = penawaran_collection.find_one({'_id': ObjectId(offer_id)})
    
    if action == 'confirm':
        penawaran_collection.update_one({'_id': ObjectId(offer_id)}, {'$set': {'status': 'telah diambil'}})
    elif action == 'accept':
        penawaran_collection.update_one({'_id': ObjectId(offer_id)}, {'$set': {'status': 'menunggu pengambilan'}})
    elif action == 'reject':
        penawaran_collection.update_one({'_id': ObjectId(offer_id)}, {'$set': {'status': 'menunggu', 'price': offer['initial_price']}})
    
    return redirect(url_for('jual'))

def save_offer():
    user = users_collection.find_one({'phone': session.get('phone')})
    waktu = datetime.now()
    dist = users_collection.find({'phone':session.get('distributor')})
    offer_data = {
        'petani': session.get('username'),
        'phone': session.get('phone'),
        'commodity': session.get('commodity'),
        'quantity': session.get('quantity'),
        'price': session.get('price'),
        'initial_price': session.get('price'),
        'file': session.get('file'),
        'distributor': session.get('distributor'),
        'status': 'belum terjual', 
        'waktu' : waktu,
        'province': user['province'],
        'city': user['city'],
        'subdistrict': user['subdistrict'],
        'village': user['village'],
        'address': user['address']
    }
    penawaran_collection.insert_one(offer_data)
    flash('Offer saved successfully!', 'success')

@app.route('/penawaran')
def penawaran():
    user = users_collection.find_one({'phone' : session.get('phone')})
    offers = list(penawaran_collection.find({'distributor': session.get('username'),'status': {'$ne': 'telah diambil'}}))
    provinsi = list(provinsi_collection.find({}))
    offers_list = []
    for offer in offers:
        offer['_id'] = str(offer['_id'])
        offers_list.append(offer)

    return render_template('penawaran.html', offers=offers_list, provinsi=provinsi, results=[], show_results=False, user=user)

@app.route('/search_penawaran', methods=['POST'])
def search_penawaran():
    user = users_collection.find_one({'phone' : session.get('phone')})
    provinsi = list(provinsi_collection.find({}))
    province_id = request.form['province']
    kabupaten_id = request.form['kabupaten']
    kecamatan_id = request.form['kecamatan']
    desa_id = request.form['desa']

    province = provinsi_collection.find_one({'id': province_id})
    kabupaten = kabupaten_collection.find_one({'id': kabupaten_id})
    kecamatan = kecamatan_collection.find_one({'id': kecamatan_id})
    desa = desa_collection.find_one({'id': desa_id})
 
    query = {}
    if province:
        query['province'] = province['name'] if province else ''
    if kabupaten:
        query['city'] = kabupaten['name'] if kabupaten else ''
    if kecamatan:
        query['subdistrict'] = kecamatan['name'] if kecamatan else ''
    if desa:
        query['village'] = desa['name'] if desa else ''

    query['status'] = {'$in': ['belum terjual', 'ditawar']}
    search_results = list(penawaran_collection.find(query))
    results_list = []
    for result in search_results:
        result['_id'] = str(result['_id'])
        results_list.append(result)

    offers = list(penawaran_collection.find({'distributor': session.get('username')}))
    offers_list = []
    for offer in offers:
        offer['_id'] = str(offer['_id'])
        offers_list.append(offer)

    return render_template('penawaran.html', offers=offers_list, results=results_list, show_results=True, provinsi=provinsi, kabupaten=kabupaten, kecamatan=kecamatan, user=user)

@app.route('/get_kabupaten/<province_id>')
def get_kabupaten(province_id):
    kabupaten = list(kabupaten_collection.find({'province_id': province_id}))
    kabupaten_list = [{'id': kab['id'], 'name': kab['name']} for kab in kabupaten]
    return jsonify(kabupaten_list)

@app.route('/get_kecamatan/<regency_id>')
def get_kecamatan(regency_id):
    kecamatan = list(kecamatan_collection.find({'regency_id': regency_id}))
    kecamatan_list = [{'id': kec['id'], 'name': kec['name']} for kec in kecamatan]
    return jsonify(kecamatan_list)

@app.route('/get_desa/<district_id>')
def get_desa(district_id):
    desa = list(desa_collection.find({'district_id': district_id}))
    desa_list = [{'id': des['id'], 'name': des['name']} for des in desa]
    return jsonify(desa_list)

@app.route('/update_offer_status', methods=['POST'])
def update_offer_status():
    offer_id = request.form['offer_id']
    action = request.form['action']
    offer = penawaran_collection.find_one({'_id': ObjectId(offer_id)})
    
    if action == 'sell':
        penawaran_collection.update_one({'_id': ObjectId(offer_id)}, {'$set': {'status': 'menunggu pengambilan'}})
    elif action == 'reject':
        penawaran_collection.update_one({'_id': ObjectId(offer_id)}, {'$set': {'status': f'ditolak ({session.get("username")})'}})
    elif action == 'offer':
        new_price = request.form['new_price']
        penawaran_collection.update_one({'_id': ObjectId(offer_id)}, {'$set': {'price': new_price, 'status': 'ditawar'}})
    
    return redirect(url_for('penawaran'))


@app.route('/search', methods=['POST'])
def search():
    user = users_collection.find_one({'phone' : session.get('phone')})
    query = request.form.get('query')
    results = list(berita_collection.find({"judul": {"$regex": query, "$options": "i"}}))
    total_data = len(results)
    halaman = request.args.get('page', 1, type=int)
    ukuran_halaman = request.args.get('page_size', 5, type=int)
    total_halaman = (total_data + ukuran_halaman - 1) // ukuran_halaman
    skip = (halaman - 1) * ukuran_halaman
    results_page = results[skip:skip + ukuran_halaman]

    return render_template('berita.html', query=query, results=results_page, halaman=halaman, ukuran_halaman=ukuran_halaman, total_halaman=total_halaman, user=user)

@app.route('/berita')
def show_data():
    user = users_collection.find_one({'phone': session.get('phone')})
    role = session.get('role')
    halaman = request.args.get('page', 1, type=int)
    ukuran_halaman = request.args.get('page_size', 5, type=int)
    total_data = berita_collection.count_documents({})
    total_halaman = (total_data + ukuran_halaman - 1) // ukuran_halaman
    skip = (halaman - 1) * ukuran_halaman
    data = list(berita_collection.find().skip(skip).limit(ukuran_halaman))
    return render_template('berita.html', data=data, halaman=halaman, ukuran_halaman=ukuran_halaman, total_halaman=total_halaman, user=user,role=role)

@app.route('/berita/<judul>', methods=['GET', 'POST'])
def tampilkan_berita(judul):
    user = users_collection.find_one({'phone': session.get('phone')})
    role = session.get('role')
    judul = judul.replace('%20', ' ')
    berita = berita_collection.find_one({'judul': judul})
    if not berita:
        return "Berita tidak ditemukan.", 404

    if request.method == 'POST':
        nama = session.get('nama')
        teks = request.form.get('teks')
        parent_id = request.form.get('parent_id')
        waktu = datetime.now().isoformat()
        img = user['image']

        komentar = {
            "_id": str(uuid.uuid4()),
            "nama": nama,
            "teks": teks,
            "waktu": waktu,
            "image": img,
            "likes": 0,
            "dislikes": 0,
            "replies": [],
            "pinned": False
        }

        if parent_id:
            berita_collection.update_one(
                {'judul': judul, 'komentar': {'$elemMatch': {'_id': parent_id}}},
                {'$push': {'komentar.$.replies': komentar}}
            )
        else:
            berita_collection.update_one(
                {'judul': judul},
                {'$push': {'komentar': komentar}}
            )

        return redirect(url_for('tampilkan_berita', judul=judul, role=role, user=user))

    sort_by = request.args.get('sort_by', 'terbaru')

    if 'komentar' in berita:
        if sort_by == 'terpopuler':
            berita['komentar'] = sorted(berita['komentar'], key=lambda k: k.get('likes', 0), reverse=True)
        elif sort_by == 'terbaru':
            berita['komentar'] = sorted(berita['komentar'], key=lambda k: k.get('waktu', ''), reverse=True)
        elif sort_by == 'disematkan':
            berita['komentar'] = sorted(berita['komentar'], key=lambda k: k.get('pinned', False), reverse=True)

    return render_template('iniberita.html', berita=berita, sort_by=sort_by, role=role, user=user)

@app.route('/like_comment', methods=['POST'])
def like_comment():
    data = request.get_json()
    judul = data.get('judul')
    komentar_id = data.get('komentar_id')
    action = data.get('action')
    
    if judul and komentar_id and action in ['like', 'dislike']:
        update = {'$inc': {'komentar.$[elem].' + action + 's': 1}}
        berita_collection.update_one({'judul': judul}, update, array_filters=[{'elem._id': komentar_id}])        
        return jsonify(success=True)
    else:
        return jsonify(success=False, error='Invalid request data')


def serialize_doc(doc):
    """Convert MongoDB document to a serializable format."""
    doc['_id'] = str(doc['_id'])
    return doc

@app.route('/catatan')
def catatan():
    user = users_collection.find_one({'phone': session.get('phone')})
    phone = session.get('phone')
    panen_data = [serialize_doc(doc) for doc in catatan_collection.find({'phone': phone}).sort("tanggal_panen", -1).limit(10)]
    jual_data = [serialize_doc(doc) for doc in catatan_collection.find({'phone': phone}).sort("tanggal_panen", -1).limit(10)]
    history_data = [serialize_doc(doc) for doc in catatan_collection.find({'phone': phone}).sort("tanggal_panen", -1).limit(10)]
    return render_template('catatan.html', panen_data=panen_data, jual_data=jual_data, history_data=history_data, user=user)

@app.route('/add_data', methods=['POST'])
def add_data():
    try:
        user = users_collection.find_one({'phone': session.get('phone')})
        tanggal_panen = request.form['tanggal_panen']
        jumlah_dijual = int(request.form['jumlah_dijual'])
        jumlah_panen = int(request.form['jumlah_panen'])
        harga_jual = int(request.form['harga_jual'])
        commodity = request.form['commodity']
        tanggal_panen_dt = datetime.strptime(tanggal_panen, '%Y-%m-%d')

        new_data = {
            'petani': session.get('username'),
            'phone': session.get('phone'),
            'tanggal_panen': tanggal_panen_dt,
            'jumlah_dijual': jumlah_dijual,
            'jumlah_panen': jumlah_panen,
            'harga_jual': harga_jual,
            'commodity': commodity,
            'province': user['province'],
            'city': user['city'],
            'subdistrict': user['subdistrict'],
            'village': user['village'],
            'address': user['address']
        }
        catatan_collection.insert_one(new_data)
        return redirect(url_for('catatan'))
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/update_data', methods=['POST'])
def update_data():
    try:
        doc_id = request.form['doc_id']
        tanggal_panen = request.form['tanggal_panen']
        jumlah_dijual = int(request.form['jumlah_dijual'])
        jumlah_panen = int(request.form['jumlah_panen'])
        harga_jual = int(request.form['harga_jual'])
        commodity = request.form['commodity']
        tanggal_panen_dt = datetime.strptime(tanggal_panen, '%Y-%m-%d')

        updated_data = {
            'tanggal_panen': tanggal_panen_dt,
            'jumlah_dijual': jumlah_dijual,
            'jumlah_panen': jumlah_panen,
            'harga_jual': harga_jual,
            'commodity': commodity
        }
        catatan_collection.update_one({'_id': ObjectId(doc_id)}, {'$set': updated_data})
        return redirect(url_for('catatan'))
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/komunitas')
def komunitas():
    provinsi = provinsi_collection.find({})
    desa = desa_collection.find_one({'name': session.get('desa') })
    user = users_collection.find_one({'phone':session.get('phone')})
    kabupaten = user['city']
    
    komunitas_data = []
    catatan = list(catatan_collection.find({'city':kabupaten}).limit(50))
    komoditas = {doc['commodity'] for doc in catatan}
    if catatan:
        komunitas_data.append({
            'komoditas': list(komoditas),
        })

    return render_template('komonitas.html', komunitas_data=komunitas_data, user=user, provinsi=provinsi, desa=desa)

@app.route('/search_komunitas', methods=['POST'])
def search_komunitas():
    user = users_collection.find_one({'phone': session.get('phone')})
    provinsi = list(provinsi_collection.find({}))
    province_id = request.form['province']
    kabupaten_id = request.form['kabupaten']
    kecamatan_id = request.form['kecamatan']
    desa_id = request.form['desa']

    province = provinsi_collection.find_one({'id': province_id})
    kabupaten = kabupaten_collection.find_one({'id': kabupaten_id})
    kecamatan = kecamatan_collection.find_one({'id': kecamatan_id})
    desa = desa_collection.find_one({'id': desa_id})
    des = desa['name']
    condition = {'village': des }
    distinct_count = len(list(users_collection.distinct('phone', filter=condition)))

    query = {}
    if province:
        query['province'] = province['name']
    if kabupaten:
        query['city'] = kabupaten['name']
    if kecamatan:
        query['subdistrict'] = kecamatan['name']
    if desa:
        query['village'] = desa['name']

    panen_data = [serialize_doc(doc) for doc in catatan_collection.find(query).sort("tanggal_panen", -1).limit(50)]
    jual_data = [serialize_doc(doc) for doc in catatan_collection.find(query).sort("tanggal_panen", -1).limit(50)]
    history_data = [serialize_doc(doc) for doc in catatan_collection.find(query).sort("tanggal_panen", -1).limit(50)]

    data_exists = len(panen_data) > 0 or len(jual_data) > 0

    return render_template('komonitas.html', panen_data=panen_data, jual_data=jual_data, history_data=history_data, user=user, provinsi=provinsi, show_results=True, data_exists=data_exists, desa=desa, distinct_count=distinct_count)



@app.route('/info')
def charts():
    user = users_collection.find_one({'phone': session.get('phone')})
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('infoH.html', current_date=current_date, user=user)




if __name__ == '__main__':
    app.secret_key = 'your_secret_key'
    app.run(debug=True)
