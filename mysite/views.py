from django.shortcuts import render, redirect
from mysite import models,forms
from django.core.mail import EmailMessage
import json, urllib
from django.conf import settings
from django.contrib import messages
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from plotly.offline import plot
import plotly.graph_objs as go
import numpy as np
import os
import pymongo

def index(request):
    posts = models.Post.objects.filter(enabled=True).order_by('-pub_time')[:30]
    moods = models.Mood.objects.all()
    try:
        user_id = request.GET['user_id']
        user_pass = request.GET['user_pass']
        user_post = request.GET['user_post']
        user_mood = request.GET['mood']
    except:
        user_id = None
        message = '如要張貼訊息，則每一個欄位都要填...'

    if user_id != None:
        mood = models.Mood.objects.get(status=user_mood)
        post = models.Post(mood=mood, nickname=user_id, del_pass=user_pass, message=user_post)
        post.save()
        message='成功儲存！請記得你的編輯密碼[{}]!，訊息需經審查後才會顯示。'.format(user_pass)
    
    if request.user.is_authenticated:
        username = request.user.username
        useremail = request.user.email
        try:
            user = User.objects.get(username=username)
            diaries = models.Diary.objects.filter(user=user).order_by('-ddate')
        except Exception as e:
            print(e)
            pass
    messages.get_messages(request)
    return render(request, 'index.html', locals())

def delpost(request, pid=None, del_pass=None):
    if del_pass and pid:
        try:
            post = models.Post.objects.get(id=pid)
            if post.del_pass == del_pass:
                post.delete()
        except:
            pass
    return redirect('/')

def listing(request):
    posts = models.Post.objects.filter(enabled=True).order_by('-pub_time')[:150]
    moods = models.Mood.objects.all()
    return render(request, 'listing.html', locals())

def posting(request):
    moods = models.Mood.objects.all()
    message = '如要張貼訊息，則每一個欄位都要填...'
    if request.method=='POST':
        user_id = request.POST.get('user_id')
        user_pass = request.POST.get('user_pass')
        user_post = request.POST.get('user_post')
        user_mood = request.POST.get('mood')
        if user_id != None:
            mood = models.Mood.objects.get(status=user_mood)
            post = models.Post(mood=mood, nickname=user_id, del_pass=user_pass, message=user_post)
            post.save()
            return redirect("/list/")
    return render(request, "posting.html", locals())

def contact(request):
    if request.method == 'POST':
        form = forms.ContactForm(request.POST)
        if form.is_valid():
            message = "感謝您的來信，我們會儘速處理您的寶貴意見。"
            user_name = form.cleaned_data['user_name']
            user_city = form.cleaned_data['user_city']
            user_school = form.cleaned_data['user_school']
            user_email  = form.cleaned_data['user_email']
            user_message = form.cleaned_data['user_message']

            mail_body = u'''
                        網友姓名：{}
                        居住城市：{}
                        是否在學：{}
                        電子郵件：{}
                        反應意見：如下
                        {}'''.format(user_name, user_city, user_school, user_email, user_message)

            email = EmailMessage(   '來自【不吐不快】網站的網友意見', 
                                    mail_body, 
                                    user_email,
                                    ['skynet.tw@gmail.com'])
            email.send()
        else:
            message = "請檢查您輸入的資訊是否正確！"
    else:
        form = forms.ContactForm()
    return render(request, 'contact.html', locals())

def post2db(request):
    if request.method == 'POST':
        post_form = forms.PostForm(request.POST)
        if post_form.is_valid():
            recaptcha_response = request.POST.get('g-recaptcha-response')
            url = 'https://www.google.com/recaptcha/api/siteverify'
            values = {
                'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            data = urllib.parse.urlencode(values).encode()
            req =  urllib.request.Request(url, data=data)
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode())
            if result['success']:
                post_form.save()
                return redirect('/list/')
    else:
        post_form = forms.PostForm()
        message = '如要張貼訊息，則每一個欄位都要填...'          
    return render(request, 'post2db.html', locals())

def bmi(request):
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    collections = client["ch08mdb"]["bodyinfo"]
    if request.method=="POST":
        name = request.POST.get("name").strip()
        height = request.POST.get("height").strip()
        weight = request.POST.get("weight").strip()
        collections.insert_one({
            "name": name,
            "height": height,
            "weight": weight
        })
        return redirect("/bmi/")
    else:
        records = collections.find()
        data = list()
        for rec in records:
            t = dict()
            t['name'] = rec['name']
            t['height'] = rec['height']
            t['weight'] = rec['weight']
            t['bmi'] = round(float(t['weight'])/(int(t['height'])/100)**2, 2)
            data.append(t)

    return render(request, "bmi.html", locals())

def login(request):
    if request.method == 'POST':
        login_form = forms.LoginForm(request.POST)
        if login_form.is_valid():
            login_name=request.POST['username'].strip()
            login_password=request.POST['password']
            try:
                user = models.User.objects.get(name=login_name)
                if user.password == login_password:
                    request.session['username'] = user.name
                    request.session['useremail'] = user.email
                    messages.add_message(request, messages.SUCCESS, '成功登入了')
                    return redirect('/')
                else:
                    messages.add_message(request, messages.WARNING, '密碼錯誤，請再檢查一次')
            except:
                messages.add_message(request, messages.WARNING, '找不到使用者')
        else:
            messages.add_message(request, messages.INFO,'請檢查輸入的欄位內容')
    else:
        login_form = forms.LoginForm()

    return render(request, 'login.html', locals())

def logout(request):
    auth.logout(request)
    messages.add_message(request, messages.INFO, "成功登出了")
    return redirect('/')

@login_required(login_url='/login/')
def userinfo(request):
    if request.user.is_authenticated:
        username = request.user.username
        try:
            user = User.objects.get(username=username)
            userinfo = models.Profile.objects.get(user=user)
        except:
            pass
    return render(request, "userinfo.html", locals())

@login_required(login_url='/login/')
def posting(request):
    if request.user.is_authenticated:
        username = request.user.username
        useremail = request.user.email
    messages.get_messages(request)
        
    if request.method == 'POST':
        user = User.objects.get(username=username)
        diary = models.Diary(user=user)
        post_form = forms.DiaryForm(request.POST, instance=diary)
        if post_form.is_valid():
            messages.add_message(request, messages.INFO, "日記已儲存")
            post_form.save()  
            return redirect('/')
        else:
            messages.add_message(request, messages.INFO, '要張貼日記，每一個欄位都要填...')
    else:
        post_form = forms.DiaryForm()
        messages.add_message(request, messages.INFO, '要張貼日記，每一個欄位都要填...')
    return render(request, "posting.html", locals())

def votes(request):
    data = models.Vote.objects.all()
    return render(request, "votes.html", locals())


def plotly(request):
    data = models.Vote.objects.all()
    # x = np.linspace(0, 2*np.pi, 360)
    # y1 = np.sin(x)
    # y2 = np.cos(x)
    # plot_div = plot([go.Scatter(x=x, y=y1,
	# 	mode='lines', name='SIN', text="Title",
	# 	opacity=0.8, marker_color='green'),
	# 	go.Scatter(x=x, y=y2,
	# 	mode='lines', name='COS', 
	# 	opacity=0.8, marker_color='green')],
	# 	output_type='div')
    
    labels = [d.name for d in data]
    values = [d.votes for d in data]
    plot_div = plot([go.Bar(y=labels, x=values, 
                            orientation='h')], output_type='div')
    return render(request, "plotly.html", locals())

def chart3d(request):
    filename = os.path.join(settings.BASE_DIR, "3d.csv")
    with open(filename, "r", encoding="utf-8") as fp:
        rawdata = fp.readlines()
    rawdata = [(float(d.split(",")[0]),float(d.split(",")[1]), float(d.split(",")[2]), float(d.split(",")[3]))  for d in rawdata]
    chart_data = np.array(rawdata).T
    plot_div = plot([go.Scatter3d(x=chart_data[0], 
                                  y=chart_data[1], 
                                  z=chart_data[3], 
                                  mode="markers", 
                                  marker=dict(size=2, symbol='circle'))], 
                    output_type='div')
    return render(request, "chart3d.html", locals())