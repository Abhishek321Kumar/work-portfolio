<?php

include "process1.php";
session_start();


?>


<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About Us</title>
    <style>
  <?php include 'css/style.css'; ?>
    </style>
   
</head>
<body>
    <section id="navbar">
        <div class="container header">
    
         <nav>
           <div class="logo">
               <img src="images/grlogo2.svg" alt="logo">
      
      
            </div>
          
          <ul id="navmenu">
              <li><a href="http://localhost/major%20project/index.php">Home</a> </li>
              <li><a href="http://localhost/major%20project/aboutus.php">About Us</a> </li>
              <li><a href="http://localhost/major%20project/privacypolicy.php">Privacy Policy</a>  </li>
              <?php if(!isset($_SESSION['email']))
           {?>
           <li> <a href="http://localhost/major%20project/contact.php"> Contact Us</a> </li>
          <?php } ?> 
              
          </ul>
    
    
    
         </nav>        
       
    
    
        </div>

    
    
    
       </section>

       <section id="aboutus">

               <div class="container">
               

                <div class="aboutbox">
                    <h1>About us</h1>

                    <div class="back">  </div>

                    <img src="images/grlogo2.svg" id="company" alt="logo">

                    <p>We are introducing a new step in the world of recycling by adding digital mode of communication for recycling service.
                       We work on E-waste which can be toxic, is not biodegradable and accumulates in the environment, in the soil, air, 
                       water and living things. E-Waste if recycled properly can yield some important metals like gold, silver, copper, palladium etc.
                        We proudly believe in our tag line that is ‘RRR’ which stands for ‘Reduce, Recycle and Reuse’. Here at Green Recyclers, we
                         aim at reducing the hazardous e-waste by recycling it in order to keep our environment clean by reusing it. We stand out 
                         from the crowd as we believe in 2 mantras: customer satisfaction and save nature. We provide our customers door 
                      pick up service for their e-waste. We are a growing family with many satisfied customers. We currently have services over four states 
                    <b>Andra Pradesh</b>, <b>Kerala </b>, <b>Karnataka </b> and  <b>Tamil Nadu </b>. </p>


                     <div id="creator">
                        <h2>Creators</h2>
                        <div class="creators">

                         
                            <div>
           
                               <img src="images/person1.jpg"   alt="creator" >    
                               <ul><li>Aashish Kumar</li>
                                <li>BCA from Presidency College</li>
                                <li>ashmkumar@gmail.com</li>

                            </ul>                  
                            </div>
                            <div>
           
                               <img src="images/person2.jpg"   alt="creator" >       
                               <ul><li>Abhishek Anil Kumar</li>
                                          <li>BCA from Presidency College</li>
                                          <li>jithuaakabhishek123@gmail.com</li>

                                      </ul>      
                            </div>
                          </div>


                     </div>
                       
                </div>

            


               </div>



       </section>


       
    <section id="footer" class="footer">
        <div class="heading2">
         <h2> QuickLinks</h2>
        </div> 
         
         
         <div class="container">
           
            <div class="quicklinks">
   
                <ul>
   
                 <li><a href="http://localhost/major%20project/aboutus.php"> About Us</a></li>
                </ul>
   
                <?php if(!isset($_SESSION['email']))
                  {   ?>
                <ul>
           <li> <a href="http://localhost/major%20project/contact.php"> Contact Us</a> </li>
       
                </ul>
                <?php } ?> 
   
   
   
                <ul>
   
                 <li><a href="http://localhost/major%20project/privacypolicy.php"> Privacy Policy</a></li>
                </ul>
   
   
                <ul>
   
                 <li><a href="sale/wanttobuy.php"> Want to Buy?</a></li>
                </ul>
   
   
                </div>
            </div>
   
        
   
     <div class="footlogo">
   
   <img src="images/grlogo2.svg" alt="logo">
     </div>
       </section>

    <?php   include "user module/activesession.php "; ?>

</body>
</html>
